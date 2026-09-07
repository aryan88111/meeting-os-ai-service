from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging
from app.services.llm.factory import LLMProviderFactory
from app.core.config import settings

logger = logging.getLogger("intelligence-endpoint")
router = APIRouter()

class MeetingContext(BaseModel):
    id: str
    title: str
    date: Optional[str] = None
    executive_summary: Optional[str] = None
    summary: Optional[str] = None
    risks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    decisions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    action_items: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    topics: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    open_questions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    transcript_snippets: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

class SynthesizeRequest(BaseModel):
    query: str
    meetings_context: List[MeetingContext]
    conversation_history: Optional[List[Dict[str, str]]] = Field(default_factory=list)

class SynthesizeResponse(BaseModel):
    answer: str
    confidence: float = 1.0
    highlighted_meeting_ids: List[str] = Field(default_factory=list)

def _build_intelligent_fallback_response(query: str, meetings: List[MeetingContext]) -> SynthesizeResponse:
    """
    Generates industry-grade, descriptive, and structured analytical responses
    when direct LLM inference is unavailable or in offline environments.
    """
    q_lower = query.lower()
    
    # Check for comparative/risk-specific intent
    is_risk_query = any(w in q_lower for w in ["risk", "danger", "blocker", "obstacle", "threat", "issue", "severity"])
    is_comparative = any(w in q_lower for w in ["only", "other", "all", "across", "compare", "which meeting", "every"])
    is_decision_query = any(w in q_lower for w in ["decision", "decided", "why", "rationale", "agree", "chose", "architecture"])
    is_action_query = any(w in q_lower for w in ["action", "task", "assigned", "deadline", "todo", "status", "who is doing"])
    
    highlighted_ids = []

    # 1. Comparative / Cross-Meeting Risk Auditing
    if is_risk_query:
        meetings_with_risks = []
        meetings_without_risks = []

        for m in meetings:
            if m.risks and len(m.risks) > 0:
                meetings_with_risks.append(m)
                highlighted_ids.append(m.id)
            else:
                meetings_without_risks.append(m)

        lines = []
        if is_comparative:
            lines.append("### Direct Answer\n")
            if len(meetings_with_risks) == 0:
                lines.append("No active risks or technical blockers have been flagged across any recorded meetings in your workspace.")
            elif len(meetings_with_risks) == 1:
                single_m = meetings_with_risks[0]
                lines.append(f"**No, only \"{single_m.title}\" has recorded risks.** Across all **{len(meetings)} meeting sessions** evaluated in your workspace, no other meetings have registered risks or blockers.")
            else:
                lines.append(f"**Risks were identified across {len(meetings_with_risks)} of {len(meetings)} meetings.** Risks are not isolated to a single session.")

            lines.append("\n### Detailed Risk Breakdown\n")
            for m in meetings_with_risks:
                lines.append(f"#### In \"{m.title}\" ({m.date or 'Recorded'}):")
                for r in m.risks or []:
                    desc = r.get("description", "Identified risk")
                    sev = r.get("severity", "MEDIUM")
                    mit = r.get("mitigation")
                    lines.append(f"- **[{sev} Priority]** {desc}")
                    if mit:
                        lines.append(f"  *Mitigation Strategy:* {mit}")
                lines.append("")

            if len(meetings_without_risks) > 0:
                clean_titles = ", ".join([f'\"{m.title}\"' for m in meetings_without_risks[:6]])
                lines.append(f"### Meetings with No Identified Risks\n")
                lines.append(f"The following {len(meetings_without_risks)} meetings have **zero flagged risks or blockers**: {clean_titles}.")

            return SynthesizeResponse(
                answer="\n".join(lines).strip(),
                confidence=0.95,
                highlighted_meeting_ids=highlighted_ids
            )
        else:
            lines.append("### Identified Risks Across Workspace Meetings\n")
            if len(meetings_with_risks) == 0:
                lines.append("There are currently no recorded risks or blockers found in your meeting transcripts.")
            else:
                for m in meetings_with_risks:
                    lines.append(f"**\"{m.title}\"** ({m.date or 'Recent'}):")
                    for r in m.risks or []:
                        desc = r.get("description", "")
                        sev = r.get("severity", "MEDIUM")
                        mit = r.get("mitigation")
                        lines.append(f"- **[{sev}]** {desc}")
                        if mit:
                            lines.append(f"  *Mitigation:* {mit}")
                    lines.append("")

            return SynthesizeResponse(
                answer="\n".join(lines).strip(),
                confidence=0.92,
                highlighted_meeting_ids=highlighted_ids
            )

    # 2. Decision & Architecture Queries
    if is_decision_query:
        lines = ["### Recorded Decisions & Architectural Context\n"]
        meetings_with_decisions = [m for m in meetings if m.decisions and len(m.decisions) > 0]
        
        if len(meetings_with_decisions) == 0:
            lines.append("No formal decisions have been logged in the meeting records matching this topic.")
        else:
            for m in meetings_with_decisions:
                highlighted_ids.append(m.id)
                lines.append(f"#### In \"{m.title}\" ({m.date or 'Recorded'}):")
                for d in m.decisions or []:
                    decision = d.get("decision", "")
                    context = d.get("context")
                    lines.append(f"- **Decision:** {decision}")
                    if context:
                        lines.append(f"  *Rationale / Context:* {context}")
                lines.append("")

        return SynthesizeResponse(
            answer="\n".join(lines).strip(),
            confidence=0.94,
            highlighted_meeting_ids=highlighted_ids
        )

    # 3. Action Items & Assignments
    if is_action_query:
        lines = ["### Action Items & Task Accountability\n"]
        meetings_with_actions = [m for m in meetings if m.action_items and len(m.action_items) > 0]
        
        if len(meetings_with_actions) == 0:
            lines.append("No pending action items or tasks were extracted from the searched meetings.")
        else:
            for m in meetings_with_actions:
                highlighted_ids.append(m.id)
                lines.append(f"#### In \"{m.title}\":")
                for a in m.action_items or []:
                    desc = a.get("description", "")
                    assignee = a.get("assigneeName") or a.get("assignee_name") or "Unassigned"
                    status = a.get("status", "PENDING")
                    priority = a.get("priority", "MEDIUM")
                    lines.append(f"- **{desc}** — Assigned to **{assignee}** `[{status} | {priority}]`")
                lines.append("")

        return SynthesizeResponse(
            answer="\n".join(lines).strip(),
            confidence=0.93,
            highlighted_meeting_ids=highlighted_ids
        )

    # 4. General Multi-Meeting Synthesis
    lines = [f"### Workspace Meetings Overview\n"]
    if len(meetings) == 0:
        return SynthesizeResponse(
            answer="No meeting records were available to synthesize an answer.",
            confidence=0.5,
            highlighted_meeting_ids=[]
        )

    lines.append(f"Across your organization workspace, there are **{len(meetings)} meeting sessions** recorded. Below is a structured summary of each discussion:\n")

    for idx, m in enumerate(meetings, 1):
        highlighted_ids.append(m.id)
        date_str = m.date or 'Recorded Session'
        lines.append(f"---\n")
        lines.append(f"#### {idx}. **\"{m.title}\"** ({date_str})")
        
        if m.executive_summary:
            lines.append(f"{m.executive_summary}\n")
        elif m.summary:
            lines.append(f"{m.summary}\n")

        # Add relevant topics if present
        if m.topics:
            lines.append("**Key Topics:**")
            for t in m.topics[:3]:
                title = t.get("title", "")
                summary = t.get("summary", "")
                lines.append(f"- **{title}**: {summary}")
            lines.append("")

        # Add decisions if present
        if m.decisions:
            lines.append("**Key Decisions:**")
            for d in m.decisions[:2]:
                lines.append(f"- {d.get('decision', '')}")
            lines.append("")

        # Add action items if present
        if m.action_items:
            lines.append("**Action Items:**")
            for a in m.action_items[:2]:
                desc = a.get("description", "")
                assignee = a.get("assigneeName") or a.get("assignee_name") or "Unassigned"
                lines.append(f"- **{desc}** (*Assigned to {assignee}*)")
            lines.append("")

    return SynthesizeResponse(
        answer="\n".join(lines).strip(),
        confidence=0.95,
        highlighted_meeting_ids=highlighted_ids[:8]
    )

@router.post("/synthesize", response_model=SynthesizeResponse, status_code=status.HTTP_200_OK)
async def synthesize_knowledge_answer(request: SynthesizeRequest) -> SynthesizeResponse:
    """
    RAG Synthesis Endpoint.
    Analyzes multi-meeting context and generates rich, descriptive, grounded markdown answers.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    logger.info(f"Synthesizing RAG answer for query: '{request.query}' across {len(request.meetings_context)} meetings")

    # Try calling LLM Provider if available
    try:
        provider = LLMProviderFactory.get_provider()
        
        # Build comprehensive grounded prompt for the LLM
        context_blocks = []
        for idx, m in enumerate(request.meetings_context, 1):
            block = [f"=== Meeting {idx}: \"{m.title}\" (ID: {m.id}, Date: {m.date or 'N/A'}) ==="]
            if m.executive_summary:
                block.append(f"Executive Summary: {m.executive_summary}")
            if m.summary:
                block.append(f"Detailed Summary: {m.summary}")
            if m.topics:
                block.append(f"Topics: {m.topics}")
            if m.decisions:
                block.append(f"Decisions: {m.decisions}")
            if m.action_items:
                block.append(f"Action Items: {m.action_items}")
            if m.risks:
                block.append(f"Risks & Obstacles: {m.risks}")
            if m.open_questions:
                block.append(f"Open Questions: {m.open_questions}")
            if m.transcript_snippets:
                block.append(f"Relevant Transcript Segments: {m.transcript_snippets}")
            context_blocks.append("\n".join(block))

        full_context_str = "\n\n".join(context_blocks)

        system_prompt = (
            "You are MeetingOS Knowledge Assistant, an enterprise-grade AI that analyzes organization meeting intelligence.\n"
            "Your instructions:\n"
            "1. Answer the user's question directly, clearly, and descriptively using markdown formatting.\n"
            "2. When the user asks comparative or multi-meeting questions (e.g., 'only this meeting has risk not other?'), explicitly analyze ALL provided meetings, comparing which have risks/decisions and which do not.\n"
            "3. Ground all answers strictly in the provided meeting data. Never invent meetings or facts.\n"
            "4. Organize your response with clear markdown headers, such as '### Direct Answer', '### Detailed Analysis', and '### Actionable Takeaways'.\n"
            "5. Cite specific meeting titles, speaker quotes, risk severities, or mitigations where applicable."
        )

        user_prompt = f"User Question: {request.query}\n\nMeeting Intelligence Data:\n{full_context_str}"

        # If LLM text generation returns a real synthesis, return it
        llm_response = await provider.generate_text(prompt=user_prompt, system_prompt=system_prompt)
        
        if llm_response and llm_response != "Simulated LLM response":
            highlighted = [m.id for m in request.meetings_context[:4]]
            return SynthesizeResponse(
                answer=llm_response.strip(),
                confidence=0.96,
                highlighted_meeting_ids=highlighted
            )
    except Exception as e:
        logger.warning(f"LLM Provider synthesis encountered exception, falling back to analytical engine: {e}")

    # High-grade deterministic fallback synthesizer
    return _build_intelligent_fallback_response(request.query, request.meetings_context)
