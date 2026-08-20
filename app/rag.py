"""
Lightweight RAG system for GFC 10-K financial analysis.
- build_chunks(): converts DataFrames + narrative into labeled text chunks
- retrieve():     scores chunks by relevance to the user question
- ask_chatbot():  injects top chunks into a grounded Gemini prompt
"""

import pandas as pd
from google import genai
from google.genai import types


# ---------------------------------------------------------------------------
# Chunk builder
# ---------------------------------------------------------------------------

def build_chunks(raw: pd.DataFrame, ratios: pd.DataFrame) -> list[dict]:
    """Build all knowledge chunks from raw data, ratios, and narrative insights."""
    chunks = []

    # --- Raw financials: one chunk per company per fiscal year ---
    for _, row in raw.iterrows():
        company = str(row["Company"]).strip()
        fy = str(row["FiscalYear "]).strip() if "FiscalYear " in raw.columns else str(row["FiscalYear"]).strip()
        text = (
            f"{company} {fy} financials: "
            f"Revenue ${row['Revenue ($mm)']:,.0f}M, "
            f"Gross Profit ${row['GrossProfit ($mm)']:,.0f}M, "
            f"Operating Income ${row['Operating Income ($mm)']:,.0f}M, "
            f"Net Income ${row['Net Income ($mm)']:,.0f}M, "
            f"Total Assets ${row['Total Assets ($mm)']:,.0f}M, "
            f"Total Equity ${row['Total Equity ($mm)']:,.0f}M, "
            f"Operating Cash Flow ${row['Operating Cash Flow ($mm)']:,.0f}M, "
            f"CapEx ${row['CapEx ($mm)']:,.0f}M."
        )
        chunks.append({
            "id": f"{company}_{fy}_raw",
            "company": company,
            "year": fy,
            "topic": "financials",
            "text": text,
        })

    # --- Ratios: one chunk per company per fiscal year ---
    for _, row in ratios.iterrows():
        company = str(row["Company"]).strip()
        fy = str(row["FiscalYear"]).strip()
        text = (
            f"{company} {fy} ratios: "
            f"Gross Margin {row['Gross Margin %'] * 100:.1f}%, "
            f"Operating Margin {row['Operating Margin %'] * 100:.1f}%, "
            f"Net Margin {row['Net Margin %'] * 100:.1f}%, "
            f"ROE {row['ROE %'] * 100:.1f}%, "
            f"ROA {row['ROA %'] * 100:.1f}%, "
            f"Current Ratio {row['Current Ratio']:.2f}, "
            f"Debt-to-Equity {row['Debt-to-Equity']:.2f}, "
            f"Free Cash Flow ${row['Free Cash Flow ($mm)']:,.0f}M, "
            f"Revenue Growth {row['Revenue Growth % (YoY)'] * 100:.1f}%."
        )
        chunks.append({
            "id": f"{company}_{fy}_ratios",
            "company": company,
            "year": fy,
            "topic": "ratios",
            "text": text,
        })

    # --- Narrative analysis: one chunk per company + cross-company ---
    narrative_chunks = [
        {
            "id": "Microsoft_narrative",
            "company": "Microsoft",
            "year": "all",
            "topic": "analysis",
            "text": (
                "Microsoft analysis: Strongest all-around performer. "
                "Highest net margins (~36%), fastest revenue growth (~15% YoY in FY2025), "
                "lowest leverage (D/E ~0.80). Revenue growth nearly doubled from 6.9% (FY2023) to 14.9% (FY2025). "
                "Gross margin held flat at ~69% despite heavy AI/cloud investment — evidence of operating leverage. "
                "Simultaneous improvement in margin, growth, and leverage. Verdict: Strong."
            ),
        },
        {
            "id": "Apple_narrative",
            "company": "Apple",
            "year": "all",
            "topic": "analysis",
            "text": (
                "Apple analysis: Stable and improving. Revenue growth swung from -2.8% (FY2023) to +6.4% (FY2025). "
                "Net margin expanded from 25.3% to 26.9%. High D/E (~3.87) driven by share buybacks, not distress. "
                "Current ratio below 1.0 but backstopped by ~$110-118B annual operating cash flow. "
                "ROE unusually high (~152-165%) due to buybacks shrinking equity base, not operational outperformance. "
                "Verdict: Stable-Improving. Watch-item: leverage sensitivity to earnings slowdown."
            ),
        },
        {
            "id": "Tesla_narrative",
            "company": "Tesla",
            "year": "all",
            "topic": "analysis",
            "text": (
                "Tesla analysis: Most challenged. Net margin collapsed from ~15.5% (FY2023) to ~4.1% (FY2025). "
                "Revenue growth reversed from +18.8% (FY2023) to -2.9% (FY2025) — top line contracted. "
                "Operating margin fell from 9.2% to 4.6% driven by price cuts and operating cost pressure. "
                "Gross margin held near 18% throughout — compression in opex and pricing, not direct production. "
                "Low D/E (~0.67) and improving current ratio (1.73 to 2.16) suggest defensive capital discipline. "
                "Verdict: Weakening. Primary risks: profitability deterioration and revenue contraction."
            ),
        },
        {
            "id": "cross_company_narrative",
            "company": "all",
            "year": "all",
            "topic": "comparison",
            "text": (
                "Cross-company comparison FY2025: Microsoft leads on net margin (36.1%) and revenue growth (14.9%). "
                "Apple second on margin (26.9%), recovering growth (+6.4%). Tesla weakest: margin 4.1%, revenue -2.9%. "
                "In FY2023, Tesla was the fastest growing (+18.8%) — by FY2025 this fully reversed. "
                "Microsoft proves the quality-vs-speed trade-off is not inevitable — leads on both margin and growth. "
                "Apple's high leverage is a capital allocation choice (buybacks), not a distress signal. "
                "Tesla's low leverage provides limited comfort given deteriorating profitability and revenue contraction."
            ),
        },
    ]
    chunks.extend(narrative_chunks)
    return chunks


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

def retrieve(question: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """Score chunks by keyword overlap and return the top_k most relevant."""
    question_lower = question.lower()

    company_keywords = {"apple": "Apple", "microsoft": "Microsoft", "tesla": "Tesla"}
    year_keywords = ["fy2023", "fy2024", "fy2025", "2023", "2024", "2025"]
    topic_keywords = {
        "margin": ["margin", "profit", "profitability", "net income"],
        "growth": ["growth", "revenue", "growing", "decline", "trend"],
        "leverage": ["debt", "leverage", "equity", "d/e", "solvency", "buyback"],
        "liquidity": ["current ratio", "liquidity", "cash", "short-term"],
        "comparison": ["compare", "versus", "vs", "best", "worst", "highest", "lowest", "which"],
        "ratios": ["roe", "roa", "return", "ratio"],
    }

    scored = []
    for chunk in chunks:
        score = 0
        text_lower = chunk["text"].lower()

        for kw, company in company_keywords.items():
            if kw in question_lower and chunk["company"] in [company, "all"]:
                score += 3

        for yw in year_keywords:
            if yw in question_lower and (yw.upper() in chunk["year"] or chunk["year"] == "all"):
                score += 2

        for keywords in topic_keywords.values():
            for kw in keywords:
                if kw in question_lower and kw in text_lower:
                    score += 1

        if chunk["id"] == "cross_company_narrative" and any(
            w in question_lower for w in ["compare", "versus", "vs", "all", "three", "best", "which"]
        ):
            score += 4

        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [chunk for score, chunk in scored[:top_k] if score > 0]
    return top if top else chunks


# ---------------------------------------------------------------------------
# RAG entry point
# ---------------------------------------------------------------------------

def ask_chatbot(
    user_question: str,
    chunks: list[dict],
    client: genai.Client,
    top_k: int = 5,
    history: list[dict] | None = None,
) -> str:
    """
    Retrieve relevant chunks, build a grounded prompt with optional chat history,
    call Gemini, and return the answer as a string.

    history format: [{"role": "user"|"bot", "text": "..."}, ...]
    """
    relevant_chunks = retrieve(user_question, chunks, top_k=top_k)
    context = "\n\n".join([f"[{c['id']}]\n{c['text']}" for c in relevant_chunks])

    # Weave prior conversation into the prompt if provided
    history_text = ""
    if history:
        lines = []
        for turn in history:
            role = "User" if turn["role"] == "user" else "Assistant"
            lines.append(f"{role}: {turn['text']}")
        history_text = "\nCONVERSATION SO FAR:\n" + "\n".join(lines) + "\n"

    prompt = f"""You are a financial analyst assistant for Global Finance Corp (GFC).
You are analyzing 10-K filings for Apple, Microsoft, and Tesla (FY2023-FY2025).

Answer the user's question using ONLY the data provided below. Do not use outside knowledge.
If the answer isn't in the data, say so clearly rather than guessing.

DATA:
{context}
{history_text}
QUESTION: {user_question}

Answer:"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
    )

    return response.text
