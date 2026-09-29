from app.db import quotes_repo, users_repo
from app.models.quote import QuoteCreate, QuoteOut
from app.models.user import UserOut


async def resolve_customer(
    customer_id: str | None,
    customer_email: str | None,
    customer_name: str | None = None,
) -> tuple[UserOut | None, str | None]:
    """Resolve CRM user by id, email, or name.

    Returns (user, clarify_message).
    - Exact id/email wins.
    - Name: 1 match → user; 0 → not found; 2+ → clarify which email/id.
    """
    if customer_id:
        user = await users_repo.get_user_by_id(customer_id)
        if user:
            return user, None
        if not customer_email and not customer_name:
            return None, f"No customer found with id `{customer_id}`."

    if customer_email:
        user = await users_repo.get_user_by_email(customer_email)
        if user:
            return user, None
        if not customer_name:
            return None, (
                f"No customer found for {customer_email}. "
                "Import them on the Customers tab first, or use another email/name."
            )

    if customer_name:
        matches = await users_repo.find_by_name(customer_name)
        if not matches:
            return None, (
                f'No customer found named "{customer_name}". '
                "Check the Customers tab or share their email / id."
            )
        if len(matches) == 1:
            return matches[0], None
        lines = "\n".join(
            f"- {u.name} · {u.email} · id `{u.id}`" for u in matches
        )
        return None, (
            f'Multiple customers match "{customer_name}". '
            "Which one should I use? Reply with the email or id:\n"
            f"{lines}"
        )

    return None, "Please share the customer name, email, or id."


async def create_quote_for_customer(
    user: UserOut,
    origin: str,
    destination: str,
    mode: str,
    cargo: str,
    cut_off_date: str,
) -> QuoteOut:
    payload = QuoteCreate(
        customer_id=user.id,
        customer_name=user.name,
        contact_email=str(user.email),
        origin=origin,
        destination=destination,
        mode=mode,
        cargo=cargo,
        cut_off_date=cut_off_date,
    )
    return await quotes_repo.create_quote(payload)


async def list_quotes_for_customer(user: UserOut) -> list[QuoteOut]:
    return await quotes_repo.list_by_customer_id(user.id)
