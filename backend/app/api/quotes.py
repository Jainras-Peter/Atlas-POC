from datetime import date

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.db import quotes_repo
from app.models.quote import QuoteOut
from app.services.excel_export import quotes_to_xlsx

router = APIRouter(prefix="/quotes", tags=["quotes"])

XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("", response_model=list[QuoteOut])
async def list_quotes(
    customer_id: str | None = Query(default=None),
    email: str | None = Query(default=None),
) -> list[QuoteOut]:
    return await quotes_repo.list_quotes(customer_id=customer_id, email=email)


@router.get("/export")
async def export_quotes(
    format: str = Query(..., description="Export format; only xlsx/excel for now"),
    customer_id: str | None = Query(default=None),
    email: str | None = Query(default=None),
):
    fmt = format.strip().lower()
    if fmt not in {"xlsx", "excel"}:
        raise HTTPException(status_code=400, detail="Only excel format is available")

    quotes = await quotes_repo.list_quotes(customer_id=customer_id, email=email)
    if not quotes:
        raise HTTPException(status_code=404, detail="No quotes to export")

    buffer = quotes_to_xlsx(quotes)
    scope = "all"
    if customer_id:
        scope = customer_id[:8]
    elif email:
        scope = email.split("@")[0]
    filename = f"quotes-{scope}-{date.today().isoformat()}.xlsx"

    return StreamingResponse(
        buffer,
        media_type=XLSX_MEDIA,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{quote_number}", response_model=QuoteOut)
async def get_quote(quote_number: str) -> QuoteOut:
    quote = await quotes_repo.get_quote_by_number(quote_number)
    if quote is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote
