import asyncio
import json
import re
import time
import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import AsyncGroq 

app = FastAPI()

# Groq Client Initialization
# ⚠️ REPLACE WITH YOUR ACTUAL GROQ API KEY HERE ⚠️
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# Requirement #10: CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResearchRequest(BaseModel):
    patientName: str
    disease: str
    intent: str
    location: Optional[str] = "Global"
    additionalQuery: Optional[str] = ""
    history: List[dict] = []
    mode: Optional[str] = "clinical"

STOPWORDS = {
    "the", "and", "or", "for", "with", "from", "into", "onto", "in", "on", "at", "by", "to",
    "of", "a", "an", "as", "is", "are", "was", "were", "be", "been", "being", "that",
    "this", "these", "those", "it", "its", "your", "you", "we", "they", "their", "our",
    "patients", "patient", "study", "studies", "clinical", "trial", "trials", "treatment",
    "therapy", "therapies", "management", "option", "options", "latest"
}

def _normalize_text(s: Any) -> str:
    s = "" if s is None else str(s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _extract_keywords(intent: str, max_keywords: int = 12) -> List[str]:
    norm = _normalize_text(intent)
    if not norm:
        return []
    raw = [w.strip() for w in norm.split(" ") if len(w.strip()) >= 3]
    keywords = []
    for w in raw:
        if w in STOPWORDS:
            continue
        if w not in keywords:
            keywords.append(w)
        if len(keywords) >= max_keywords:
            break
    return keywords

def extract_year_from_string(date_like: Any) -> str:
    if date_like is None:
        return ""
    m = re.search(r"((?:19|20)\d{2})", str(date_like))
    return m.group(1) if m else ""

def _geo_match(user_loc: str, item: Dict[str, Any]) -> bool:
    if not user_loc:
        return False
    user_loc = str(user_loc).strip()
    if not user_loc or user_loc.lower() == "global":
        return False

    loc_norm = _normalize_text(user_loc)
    if not loc_norm:
        return False

    blob_parts = [
        item.get("location_text", ""),
        item.get("location", ""),
        item.get("title", ""),
        item.get("abstract_text", ""),
    ]
    blob = _normalize_text(" ".join([str(p) for p in blob_parts if p]))
    return loc_norm in blob

def rank_results(results: List[Dict[str, Any]], query: str, user_loc: str, intent: str) -> List[Dict[str, Any]]:
    intent_keywords = _extract_keywords(intent)
    if not results:
        return []

    ranked = []
    for item in results:
        blob = _normalize_text(" ".join([
            item.get("title", ""),
            item.get("location_text", ""),
            item.get("location", ""),
            item.get("abstract_text", ""),
        ]))

        score = 0
        if _geo_match(user_loc, item):
            score += 25 

        intent_hits = 0
        for kw in intent_keywords:
            if not kw:
                continue
            if kw in blob:
                score += 10
                intent_hits += 1

        query_norm = _normalize_text(query)
        query_score = 0
        for token in query_norm.split(" "):
            if token and len(token) >= 4 and token in blob:
                query_score += 1
        score += query_score

        item = dict(item)
        item["score"] = score
        item["intent_hits"] = intent_hits
        item["is_geo_match"] = _geo_match(user_loc, item)
        ranked.append(item)

    ranked = sorted(ranked, key=lambda x: x.get("score", 0), reverse=True)
    return ranked

async def _to_thread(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

def _requests_get_json(url: str, params: Optional[Dict[str, Any]] = None, timeout_s: int = 30) -> Dict[str, Any]:
    resp = requests.get(url, params=params, timeout=timeout_s, headers={"User-Agent": "CuraLinkHackathon/1.0"})
    resp.raise_for_status()
    return resp.json()

def _requests_post_json(url: str, payload: Dict[str, Any], timeout_s: int = 600) -> Dict[str, Any]:
    resp = requests.post(url, json=payload, timeout=timeout_s, headers={"User-Agent": "CuraLinkHackathon/1.0"})
    resp.raise_for_status()
    return resp.json()

async def get_pubmed_pool(search_term: str, target_count: int = 40) -> List[Dict[str, Any]]:
    term = quote_plus(search_term)
    retmax = max(60, target_count)

    ids: List[str] = []
    try:
        url_esearch = (
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
            f"?db=pubmed&term={term}&retmax={retmax}&retmode=json"
        )
        r = await _to_thread(_requests_get_json, url_esearch, None, 30)
        ids = r.get("esearchresult", {}).get("idlist", []) or []
    except Exception:
        ids = []

    if not ids:
        return []

    ids = [str(x) for x in ids][:target_count]
    id_str = ",".join(ids)

    title_map: Dict[str, str] = {}
    year_map: Dict[str, str] = {}
    url_esummary = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=pubmed&id={quote_plus(id_str)}&retmode=json"
    )
    try:
        esum = await _to_thread(_requests_get_json, url_esummary, None, 30)
        result = esum.get("result", {}) or {}
        for pmid, v in result.items():
            if pmid == "uids":
                continue
            try:
                title_map[str(pmid)] = v.get("title", "")
                year_map[str(pmid)] = str(v.get("pubdate", ""))[:4] if v.get("pubdate") else ""
            except Exception:
                continue
    except Exception:
        pass

    url_efetch = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pubmed&id={quote_plus(id_str)}&rettype=abstract&retmode=xml"
    )
    pool: List[Dict[str, Any]] = []
    try:
        xml_text = await _to_thread(
            lambda: requests.get(
                url_efetch,
                timeout=60,
                headers={"User-Agent": "CuraLinkHackathon/1.0"},
            ).text
        )

        root = ET.fromstring(xml_text)
        for pubmed_article in root.findall(".//PubmedArticle"):
            medline = pubmed_article.find(".//MedlineCitation")
            pmid_el = medline.find(".//PMID") if medline is not None else None
            pmid = pmid_el.text.strip() if pmid_el is not None and pmid_el.text else ""
            if not pmid:
                continue

            title = title_map.get(pmid, "")
            year = year_map.get(pmid, "")

            article_title_el = pubmed_article.find(".//ArticleTitle")
            if not title and article_title_el is not None and article_title_el.text:
                title = article_title_el.text.strip()

            abstract_text = ""
            abs_el = pubmed_article.find(".//Abstract")
            if abs_el is not None:
                parts = []
                for at in abs_el.findall(".//AbstractText"):
                    text_content = "".join(at.itertext()).strip()
                    label = at.get("Label", "")
                    if label and text_content:
                        parts.append(f"**{label.title()}:** {text_content}")
                    elif text_content:
                        parts.append(text_content)
                abstract_text = "\n\n".join(parts).strip()

            affiliations = []
            for aff_el in pubmed_article.findall(".//AffiliationInfo/Affiliation"):
                if aff_el is not None and aff_el.text:
                    affiliations.append(aff_el.text.strip())
            if not affiliations:
                for aff_el in pubmed_article.findall(".//Affiliation"):
                    if aff_el is not None and aff_el.text:
                        affiliations.append(aff_el.text.strip())

            if not year:
                pubdate = pubmed_article.find(".//PubDate")
                if pubdate is not None:
                    year = extract_year_from_string(pubdate.findtext("Year"))

            year = year or extract_year_from_string(pmid) or ""
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            location_text = " ".join(affiliations[:5]).strip()
            if abstract_text and not location_text:
                location_text = abstract_text[:600]

            pool.append({
                "title": title,
                "source": "PubMed",
                "year": year,
                "url": url,
                "location_text": location_text,
                "abstract_text": abstract_text[:2500] if abstract_text else "",
                "type": "paper"
            })
    except Exception:
        for pmid in ids:
            title = title_map.get(pmid, "")
            year = year_map.get(pmid, "")
            if not title:
                continue
            pool.append({
                "title": title,
                "source": "PubMed",
                "year": year,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "location_text": "",
                "abstract_text": "",
                "type": "paper",
            })

    if len(pool) > target_count:
        pool = pool[:target_count]
    return pool

async def get_openalex_pool(search_term: str, target_count: int = 40) -> List[Dict[str, Any]]:
    per_page = 25
    pages_needed = 2
    pool: List[Dict[str, Any]] = []

    for page in range(1, pages_needed + 1):
        if len(pool) >= target_count:
            break
        try:
            params = {
                "search": search_term,
                "per-page": per_page,
                "page": page,
            }
            data = await _to_thread(_requests_get_json, "https://api.openalex.org/works", params, 30)
            results = data.get("results", []) or []
            for w in results:
                if len(pool) >= target_count:
                    break
                wid = w.get("id", "")
                wid_short = wid.split("/")[-1] if isinstance(wid, str) and "/" in wid else wid
                title = w.get("title") or ""
                year = w.get("publication_year")
                year_str = str(year) if year is not None else ""
                url = f"https://openalex.org/{wid_short}" if wid_short else ""

                institutions = []
                for a in (w.get("authorships", []) or [])[:6]:
                    for inst in (a.get("institutions", []) or []):
                        disp = inst.get("display_name") if isinstance(inst, dict) else None
                        if disp:
                            institutions.append(str(disp))
                location_text = " ".join(institutions[:3]).strip()

                abstract_text = ""
                pool.append({
                    "title": title,
                    "source": "OpenAlex",
                    "year": year_str,
                    "url": url,
                    "location_text": location_text,
                    "abstract_text": abstract_text,
                    "type": "paper"
                })
        except Exception:
            continue

    if len(pool) > target_count:
        pool = pool[:target_count]
    return pool

async def get_clinical_trials_pool(disease: str, target_count: int = 30) -> List[Dict[str, Any]]:
    pool: List[Dict[str, Any]] = []
    try:
        params = {
            "query.cond": disease,
            "filter.overallStatus": "RECRUITING",
            "pageSize": max(30, target_count)
        }
        url = "https://clinicaltrials.gov/api/v2/studies"
        data = await _to_thread(_requests_get_json, url, params, 30)
        studies = data.get("studies", []) or []
        for s in studies:
            protocol = s.get("protocolSection", {}) or {}
            ident = protocol.get("identificationModule", {}) or {}
            contacts = protocol.get("contactsLocationsModule", {}) or {}
            status_mod = protocol.get("statusModule", {}) or {}
            eligibility_mod = protocol.get("eligibilityModule", {}) or {}

            title = ident.get("officialTitle") or ""
            nct_id = ident.get("nctId") or ""
            overall_status = status_mod.get("overallStatus") or ""
            first_post = ident.get("studyFirstPostDate") or ident.get("firstPostDate") or ""
            year = extract_year_from_string(first_post)
            
            eligibility_text = eligibility_mod.get("eligibilityCriteria", "Check URL for details")

            locations = contacts.get("locations", []) or []
            facility = "Global"
            city = ""
            state = ""
            country = ""
            if locations and isinstance(locations, list):
                loc0 = locations[0] or {}
                if isinstance(loc0, dict):
                    facility = loc0.get("facility", facility) or facility
                    city = loc0.get("city", "") or ""
                    state = loc0.get("state", "") or ""
                    country = loc0.get("country", "") or ""

            location_text = " ".join([str(facility), str(city), str(state), str(country)]).strip()
            url = f"https://clinicaltrials.gov/ct2/show/{nct_id}" if nct_id else ""

            pool.append({
                "title": title,
                "source": "ClinicalTrials.gov",
                "year": year,
                "url": url,
                "location": location_text,
                "location_text": location_text,
                "abstract_text": "",
                "status": overall_status,
                "eligibility": eligibility_text,
                "type": "trial",
                "nct_id": nct_id,
            })
    except Exception as e:
        print(f"Failed to fetch trials: {e}")

    if len(pool) > target_count:
        pool = pool[:target_count]
    return pool

def build_nearby_label(item: Dict[str, Any], user_loc: str) -> bool:
    return item.get("type") == "trial" and _geo_match(user_loc, item)

def build_llm_prompt(
    patient_name: str,
    disease: str,
    intent: str,
    location: str,
    additional_query: str,
    history: List[dict],
    ranked_pool: List[Dict[str, Any]],
    nearby_trials: List[Dict[str, Any]],
    mode: str = "clinical",
) -> Tuple[str, List[str]]:
    
    # 🔥 FIX: Reduced from 8 to 5 to avoid Groq's 6000 token limit
    llm_context_pool = ranked_pool[:5] 

    citation_list = []
    for item in llm_context_pool:
        src = item.get("source", "Source")
        yr = item.get("year", "") or "N/A"
        citation_list.append(f"[{src}, {yr}]")

    seen = set()
    citation_list_unique = []
    for c in citation_list:
        if c not in seen:
            seen.add(c)
            citation_list_unique.append(c)

    if mode == "clinical":
        style_instr = "You are a top-tier Medical Researcher. You MUST use highly technical clinical terminology. Output must be strictly data-driven, dense, and professional. Assume the reader is a doctor."
    else:
        style_instr = "You are a friendly, empathetic nurse talking to a scared patient. EXPLAIN EVERYTHING LIKE THE READER IS 5 YEARS OLD. You MUST use simple, everyday analogies. AVOID ALL COMPLEX MEDICAL JARGON. Keep sentences short and extremely easy to understand."

    final_prompt = f"""You are CuraLink Medical Intelligence.

Read this medical context carefully:
--- CONTEXT START ---
{json.dumps(llm_context_pool, ensure_ascii=False)}
Nearby trials: {json.dumps(nearby_trials[:3], ensure_ascii=False)}
--- CONTEXT END ---

Based ONLY on the context above, write a report for {patient_name} regarding {disease} and {intent} in {location}.

==================================================
CRITICAL RULES YOU MUST OBEY:
1. STRUCTURE: You MUST format your report with EXACTLY these four Markdown headings. Do not invent your own headings:
   ## Condition Overview
   ## Insights
   ## Trials
   ## Safety

2. STYLE: {style_instr}

3. CITATIONS: Cite every fact strictly using [Source, Year].
==================================================

DO NOT output "Critical rules obeyed", "Here is the report", or any other conversational filler. 
Start your response IMMEDIATELY with the exact heading "## Condition Overview".
"""
    return final_prompt, citation_list_unique

async def generate_llm_report(
    system_plus_user_prompt: str,
    citation_list: List[str],
) -> str:
    try:
        chat_completion = await groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": system_plus_user_prompt,
                }
            ],
            model="llama-3.1-8b-instant",
            temperature=0.2,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        print(f"[ERROR] Groq API Failed: {str(e)}")
        raise e

def build_fallback_report(
    patient_name: str,
    disease: str,
    intent: str,
    location: str,
    ranked_pool: List[Dict[str, Any]],
    nearby_trials: List[Dict[str, Any]],
) -> str:
    def fmt_cite(item: Dict[str, Any]) -> str:
        src = item.get("source", "Source")
        yr = item.get("year", "") or "N/A"
        return f"[{src}, {yr}]"

    top_items = ranked_pool[:8]
    top_lines = []
    for item in top_items:
        top_lines.append(f"- {item.get('title','').strip()} ({item.get('url','').strip()}) {fmt_cite(item)}")

    nearby_lines = []
    for t in nearby_trials[:5]:
        nearby_lines.append(f"- {t.get('title','').strip()} ({t.get('url','').strip()}) {fmt_cite(t)}")

    nearby_block = "\n".join(nearby_lines) if nearby_lines else "- No nearby recruiting trials identified."
    return (
        "## Condition Overview\n"
        f"{disease} research for '{intent}'. {fmt_cite(top_items[0]) if top_items else '[Source, N/A]'}\n\n"
        "## Insights\n" + "\n".join(top_lines) + "\n\n"
        "## Trials\n"
        "Nearby Clinical Opportunity\n" + nearby_block + "\n\n"
        "## Safety\n"
        "Consult with physicians based on evidence. [Source, N/A]"
    )

@app.post("/generate")
async def generate_response(data: ResearchRequest):
    pipeline_start = time.time()
    print(f"Starting Research Pipeline for {data.patientName}...")

    search_q = f"{data.disease} {data.intent} {data.additionalQuery}".strip()

    pubmed_task = get_pubmed_pool(search_q, target_count=40)
    openalex_task = get_openalex_pool(search_q, target_count=40)
    trials_task = get_clinical_trials_pool(data.disease, target_count=20)

    pubmed_pool, openalex_pool, trials_pool = await asyncio.gather(pubmed_task, openalex_task, trials_task)

    full_pool = [*pubmed_pool, *openalex_pool, *trials_pool]
    total_candidates_fetched = len(full_pool)
    print(f"[LOG] Candidates fetched: {total_candidates_fetched}")

    ranked_all = rank_results(
        results=full_pool,
        query=search_q,
        user_loc=data.location or "Global",
        intent=data.intent,
    )
    
    ranked_papers = [x for x in ranked_all if x.get("type") == "paper"]
    ranked_trials = [x for x in ranked_all if x.get("type") == "trial"]
    
    combined_top = ranked_papers[:15] + ranked_trials[:15]
    
    ranked_top = sorted(combined_top, key=lambda x: x.get("score", 0), reverse=True)

    nearby_trials = []
    for item in trials_pool:
        if build_nearby_label(item, data.location or "Global"):
            nearby_trials.append(item)

    system_plus_user_prompt, allowed_citations = build_llm_prompt(
        patient_name=data.patientName,
        disease=data.disease,
        intent=data.intent,
        location=data.location or "Global",
        additional_query=data.additionalQuery or "",
        history=data.history or [],
        ranked_pool=ranked_top,
        nearby_trials=nearby_trials,
        mode=data.mode or "clinical",
    )

    try:
        analysis_text = await generate_llm_report(system_plus_user_prompt, allowed_citations)
        return {
            "analysis": analysis_text,
            "sources": ranked_top,
            "metadata": {
                "total_candidates_fetched": total_candidates_fetched,
                "pipeline_latencyMs": int((time.time() - pipeline_start) * 1000),
            },
        }
    except Exception as e:
        print(f"[WARN] LLM failed: {str(e)}")
        fallback = build_fallback_report(data.patientName, data.disease, data.intent, data.location, ranked_top, nearby_trials)
        return {
            "analysis": fallback,
            "sources": ranked_top,
            "metadata": {
                "total_candidates_fetched": total_candidates_fetched,
                "pipeline_latencyMs": int((time.time() - pipeline_start) * 1000),
                "llm_error": str(e),
            },
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)