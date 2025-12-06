import pytest
from sqlalchemy import select
from bot.database.models import GamificationProfile, Rank
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_points_flow(db_session, services):
    """
    Caso 1: Flujo de Puntos y Rango
    * Escenario: Usuario nuevo gana 100 puntos.
    * Validación:
      * Verificar que su saldo en BD sea 100.
      * Verificar que si el Rango Plata es 100, su current_rank_id cambie.
    """
    user_id = 12345
    points_to_add = 100
    
    # Create a Silver rank with 100 points requirement
    silver_rank = Rank(
        name="Silver",
        min_points=100,
        reward_description="Silver rank reward"
    )
    db_session.add(silver_rank)
    await db_session.commit()
    await db_session.refresh(silver_rank)
    
    # Initially, user has no profile, so get_or_create_profile will create one
    # Get initial profile state
    result = await db_session.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == user_id)
    )
    initial_profile = result.scalar_one_or_none()
    
    # Since profile doesn't exist yet, it should be None
    assert initial_profile is None, "User profile should not exist initially"
    
    # Add points using the service
    await services.gamification.add_points(user_id, points_to_add, db_session)
    
    # Check that the user now has 100 points
    result = await db_session.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    
    assert profile is not None, "User profile should exist after adding points"
    assert profile.points == 100, f"User should have 100 points, got {profile.points}"
    
    # Since the silver rank requires exactly 100 points, the user should get this rank
    assert profile.current_rank_id == silver_rank.id, f"User should have silver rank, got rank id {profile.current_rank_id}"


@pytest.mark.asyncio
async def test_referral_success(db_session, services, base_rank):
    """
    Caso 2: Sistema de Referidos (Happy Path)
    * Escenario: Usuario A invita a Usuario B (nuevo).
    * Validación:
      * Usuario A tiene +100 puntos.
      * Usuario B tiene +50 puntos.
      * Usuario B tiene referred_by_id apuntando a A.
      * Usuario A tiene referrals_count = 1.
    """
    referrer_id = 11111
    referred_id = 22222

    # Create the referrer profile first
    referrer_profile = GamificationProfile(
        user_id=referrer_id,
        points=0,
        current_rank_id=base_rank.id
    )
    db_session.add(referrer_profile)
    await db_session.commit()

    # Process the referral
    referral_payload = f"ref_{referrer_id}"
    success = await services.gamification.process_referral(referred_id, referral_payload, db_session)

    # Verify referral was processed successfully
    assert success is True, "Referral processing should return True"

    # Check referrer points and referral count
    result = await db_session.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == referrer_id)
    )
    referrer = result.scalar_one_or_none()

    assert referrer is not None, "Referrer should exist"
    assert referrer.points == 100, f"Referrer should have 100 points, got {referrer.points}"
    assert referrer.referrals_count == 1, f"Referrer should have 1 referral, got {referrer.referrals_count}"

    # Check referred user points and referral source
    result = await db_session.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == referred_id)
    )
    referred = result.scalar_one_or_none()

    assert referred is not None, "Referred user should exist"
    assert referred.points == 50, f"Referred user should have 50 points, got {referred.points}"
    assert referred.referred_by_id == referrer_id, f"Referred user should have referrer ID, got {referred.referred_by_id}"


@pytest.mark.asyncio
async def test_referral_fraud(db_session, services, base_rank):
    """
    Caso 3: Sistema de Referidos (Anti-Fraude)
    * Escenario A: Usuario intenta referirse a sí mismo.
      * Resultado esperado: process_referral retorna False, puntos no cambian.
    * Escenario B: Usuario A intenta invitar a Usuario B que YA existe en el sistema.
      * Resultado esperado: process_referral retorna False, puntos no cambian.
    """
    user_id = 33333

    # Test Scenario A: Self-referral
    self_referral_payload = f"ref_{user_id}"
    success = await services.gamification.process_referral(user_id, self_referral_payload, db_session)

    # Should return False for self-referral
    assert success is False, "Self-referral should return False"

    # After self-referral check, no profile should be created initially (get_or_create_profile happens after the check)
    # But the process_referral function will call get_or_create_profile if it gets past the self-ref check
    # From the original implementation: the self-referral check prevents getting to the get_or_create_profile call
    # So the profile should not exist after a failed self-referral attempt
    result = await db_session.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    # Since the self-referral check happens first and returns early, no profile should be created
    # The original implementation checks for self-referral before creating a new profile
    assert profile is None, f"User profile should not exist after failed self-referral (profile: {profile})"

    # Test Scenario B: Refer user that already exists
    # Create a user profile with some points
    existing_user_id = 44444
    existing_profile = GamificationProfile(
        user_id=existing_user_id,
        points=50,  # Start with 50 points
        current_rank_id=base_rank.id
    )
    db_session.add(existing_profile)
    await db_session.commit()

    # Now try to refer this existing user
    referrer_id = 55555
    referral_payload = f"ref_{referrer_id}"
    success = await services.gamification.process_referral(existing_user_id, referral_payload, db_session)

    # Should return False because user already exists
    assert success is False, "Referring existing user should return False"

    # Check that existing user's points didn't change
    result = await db_session.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == existing_user_id)
    )
    updated_profile = result.scalar_one_or_none()

    assert updated_profile is not None, "Existing user profile should still exist"
    assert updated_profile.points == 50, f"Existing user points should remain unchanged, got {updated_profile.points}"


@pytest.mark.asyncio
async def test_daily_cooldown(db_session, services, base_rank):
    """
    Caso 4: Recompensa Diaria (Cooldown)
    * Escenario: Usuario reclama /daily dos veces seguidas.
    * Validación: La primera llamada retorna éxito (+50 pts), la segunda retorna error de tiempo.
    """
    user_id = 66666

    # First daily claim
    result1 = await services.gamification.claim_daily_reward(user_id, db_session)

    # First claim should be successful
    assert result1['success'] is True, "First daily claim should be successful"
    assert result1['points'] == 50, f"Daily reward should be 50 points, got {result1['points']}"

    # Check that user has gained points
    result = await db_session.execute(
        select(GamificationProfile).where(GamificationProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    assert profile is not None, "User profile should exist"
    assert profile.points >= 50, f"User should have at least 50 points, got {profile.points}"

    # Second daily claim (should fail due to cooldown)
    result2 = await services.gamification.claim_daily_reward(user_id, db_session)

    # Second claim should fail due to cooldown
    assert result2['success'] is False, "Second daily claim should fail due to cooldown"
    assert 'remaining' in result2, "Cooldown result should contain remaining time"