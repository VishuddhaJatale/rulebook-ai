import re

import streamlit as st

from backend.state_detector import StateDetector


def render_html(html):
    """
    Render raw HTML through st.markdown.

    Streamlit's Markdown parser treats any line that starts with
    4+ spaces as a fenced code block, which prints literal <div>
    tags instead of rendering them, and unsafe_allow_html=True
    does not prevent this. Since our HTML is normally written as
    an indented triple-quoted string (to match surrounding Python
    code), every call site needs its indentation stripped before
    rendering. This helper does that in one place instead of
    relying on every call site to remember it.
    """
    dedented = "\n".join(line.strip() for line in html.split("\n"))
    st.markdown(dedented, unsafe_allow_html=True)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Rulebook AI",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    :root {
        --accent-green: #3ddc97;
        --accent-green-bg: rgba(61, 220, 151, 0.10);
        --accent-amber: #f4b93f;
        --accent-amber-bg: rgba(244, 185, 63, 0.10);
        --accent-red: #ff6b6b;
        --accent-red-bg: rgba(255, 107, 107, 0.10);
        --accent-blue: #5b9dff;
        --card-bg: rgba(255, 255, 255, 0.035);
        --card-border: rgba(255, 255, 255, 0.09);
        --text-muted: #9297a2;
        --text-soft: #c8cbd2;
    }

    .block-container {
        max-width: 1100px;
        padding-top: 3rem;
        padding-bottom: 4rem;
    }

    /* ---------- Header ---------- */

    .brand {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 4px;
    }

    .brand-icon {
        font-size: 2.5rem;
    }

    .brand-title {
        font-size: 2.4rem;
        font-weight: 750;
        letter-spacing: -1px;
    }

    .subtitle {
        color: #8b8f98;
        font-size: 1.02rem;
        margin-bottom: 2.2rem;
    }

    /* ---------- Question ---------- */

    .question-label {
        font-size: 0.95rem;
        font-weight: 650;
        margin-bottom: 0.45rem;
    }

    /* ---------- State badge ---------- */

    .state-banner {
        display: flex;
        align-items: flex-start;
        gap: 0.9rem;
        padding: 1.1rem 1.3rem;
        border-radius: 12px;
        margin: 1.8rem 0 1.5rem 0;
        border: 1px solid var(--card-border);
        background: var(--card-bg);
        border-left: 4px solid var(--state-color, var(--accent-blue));
    }

    .state-icon {
        font-size: 1.6rem;
        line-height: 1.2;
    }

    .state-pill {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 750;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 0.2rem 0.55rem;
        border-radius: 999px;
        color: var(--state-color, var(--accent-blue));
        background: var(--state-color-bg, rgba(91, 157, 255, 0.10));
        margin-bottom: 0.4rem;
    }

    .state-description {
        font-size: 0.94rem;
        color: var(--text-soft);
        line-height: 1.55;
    }

    /* ---------- Answer ---------- */

    .answer-card {
        position: relative;
        padding: 1.4rem 1.6rem 1.4rem 1.9rem;
        border-radius: 12px;
        background: var(--accent-green-bg);
        border: 1px solid rgba(61, 220, 151, 0.25);
        border-left: 4px solid var(--accent-green);
        margin: 0.8rem 0 1.8rem 0;
        line-height: 1.7;
        font-size: 1.05rem;
        color: #eef1f0;
    }

    .answer-card.answer-empty {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-left: 4px solid var(--text-muted);
        color: var(--text-soft);
    }

    .not-covered-card {
        padding: 1.4rem 1.6rem 1.4rem 1.9rem;
        border-radius: 12px;
        background: var(--accent-amber-bg);
        border: 1px solid rgba(244, 185, 63, 0.25);
        border-left: 4px solid var(--accent-amber);
        margin: 0.8rem 0 1.8rem 0;
        line-height: 1.7;
        font-size: 1.02rem;
        color: #eef1f0;
    }

    .not-covered-note {
        display: inline-block;
        margin-top: 0.85rem;
        font-size: 0.82rem;
        font-weight: 650;
        color: var(--accent-amber);
        background: rgba(244, 185, 63, 0.12);
        padding: 0.3rem 0.6rem;
        border-radius: 6px;
    }

    /* ---------- Section headings ---------- */

    .section-heading {
        font-size: 1.3rem;
        font-weight: 720;
        margin-top: 1.9rem;
        margin-bottom: 0.6rem;
    }

    .section-description {
        color: var(--text-muted);
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }

    /* ---------- Source ---------- */

    .source-type {
        font-size: 0.74rem;
        font-weight: 750;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #858a95;
    }

    .source-title {
        font-size: 1.03rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }

    .source-meta {
        color: var(--text-muted);
        font-size: 0.84rem;
        margin-top: 0.3rem;
        margin-bottom: 0.9rem;
    }

    .passage {
        padding: 0.9rem 1rem;
        border-left: 3px solid #666b75;
        background: rgba(255,255,255,0.025);
        border-radius: 0 8px 8px 0;
        line-height: 1.65;
        color: #e1e3e7;
    }

    /* ---------- Contradiction ---------- */

    .conflict-row {
        display: flex;
        align-items: stretch;
        gap: 0;
        margin-bottom: 0.4rem;
    }

    .conflict-card {
        flex: 1;
        padding: 1.3rem 1.4rem;
        border-radius: 12px;
        background: var(--accent-red-bg);
        border: 1px solid rgba(255, 107, 107, 0.28);
    }

    .conflict-divider {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        flex-shrink: 0;
    }

    .conflict-divider-badge {
        width: 40px;
        height: 40px;
        border-radius: 999px;
        background: var(--accent-red);
        color: #1a1a1a;
        font-size: 0.78rem;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .conflict-source {
        font-size: 0.98rem;
        font-weight: 720;
        margin-bottom: 0.3rem;
        color: #f1f2f4;
    }

    .conflict-meta {
        color: var(--text-muted);
        font-size: 0.82rem;
        margin-bottom: 1rem;
    }

    .conflict-label {
        color: var(--text-muted);
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }

    .conflict-value {
        font-size: 2.1rem;
        font-weight: 800;
        color: var(--accent-red);
        margin: 0.1rem 0 0.7rem 0;
    }

    .conflict-summary {
        color: var(--text-soft);
        font-size: 0.88rem;
        line-height: 1.5;
    }

    .conflict-callout {
        margin: 1rem 0 0.5rem 0;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        background: rgba(255, 107, 107, 0.08);
        border: 1px dashed rgba(255, 107, 107, 0.35);
        color: var(--text-soft);
        font-size: 0.88rem;
    }

    /* ---------- Footer ---------- */

    .footer {
        text-align: center;
        color: #777c86;
        font-size: 0.8rem;
        margin-top: 3rem;
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255,255,255,0.07);
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOAD BACKEND
# ============================================================

@st.cache_resource
def load_detector():
    return StateDetector()


detector = load_detector()


# ============================================================
# STATE PRESENTATION CONFIG
# ============================================================

STATE_STYLES = {
    "ANSWERABLE": {
        "icon": "✅",
        "label": "Answerable",
        "color": "var(--accent-green)",
        "color_bg": "var(--accent-green-bg)",
        "description": (
            "The rulebook contains evidence that supports an answer "
            "to this question."
        ),
    },
    "NOT_COVERED": {
        "icon": "❓",
        "label": "Not covered",
        "color": "var(--accent-amber)",
        "color_bg": "var(--accent-amber-bg)",
        "description": (
            "The rulebook does not establish the specific information "
            "needed to answer this question."
        ),
    },
    "CONTRADICTION": {
        "icon": "⚠️",
        "label": "Contradiction detected",
        "color": "var(--accent-red)",
        "color_bg": "var(--accent-red-bg)",
        "description": (
            "The rulebook contains conflicting claims for this rule. "
            "The system will not arbitrarily pick one."
        ),
    },
}


def render_state_banner(state):
    style = STATE_STYLES.get(state)

    if not style:
        return

    render_html(
        f"""
        <div class="state-banner" style="--state-color: {style['color']}; --state-color-bg: {style['color_bg']};">
            <div class="state-icon">{style['icon']}</div>
            <div>
                <div class="state-pill">{style['label']}</div>
                <div class="state-description">{style['description']}</div>
            </div>
        </div>
        """
    )


# ============================================================
# HELPERS
# ============================================================

def clean_text(text):
    """
    Remove Markdown formatting artifacts from corpus text
    before displaying it in the UI.
    """
    if not text:
        return ""

    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"`(.*?)`", r"\1", text)

    return text.strip()


def source_name(item):
    source = item.get("source", "Unknown source")

    if source.endswith(".pdf"):
        return source.replace("_", " ").replace(".pdf", "").title()

    return source.replace("_", " ").replace(".md", "").title()


def source_meta(item):
    parts = []

    if item.get("section"):
        parts.append(str(item["section"]))

    if item.get("provision"):
        parts.append(f"§ {item['provision']}")

    if item.get("page") is not None:
        parts.append(f"Page {item['page']}")

    return "  ·  ".join(parts)


def extract_values(text):
    """
    Extract useful numeric claims such as:
    60 percent
    65%
    3 subjects
    15 July
    31 July
    """

    if not text:
        return []

    patterns = [
        r"\b\d+(?:\.\d+)?\s*%",
        r"\b\d+(?:\.\d+)?\s*percent\b",
        r"\b\d+\s+(?:subjects?|papers?|credits?|days?|weeks?)\b",
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\b",
    ]

    values = []

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for match in matches:
            cleaned = re.sub(r"\s+", " ", match).strip()

            if cleaned not in values:
                values.append(cleaned)

    return values


def render_source_passage(item):

    name = source_name(item)
    meta = source_meta(item)
    text = clean_text(item.get("text", ""))

    render_html(
        f"""
        <div class="source-type">Source</div>
        <div class="source-title">{name}</div>
        """
    )

    if meta:
        render_html(
            f'<div class="source-meta">{meta}</div>'
        )

    render_html(
        f'<div class="passage">{text}</div>'
)


def render_evidence(item, expanded=False):

    name = source_name(item)

    with st.expander(
        f"📄  {name}",
        expanded=expanded,
    ):
        render_source_passage(item)


def render_conflict_card(item):

    name = source_name(item)
    meta = source_meta(item)
    text = clean_text(item.get("text", ""))

    values = extract_values(text)

    value = values[0] if values else "Conflicting claim"

    render_html(
        f"""
        <div class="conflict-card">

            <div class="conflict-source">
                {name}
            </div>

            <div class="conflict-meta">
                {meta}
            </div>

            <div class="conflict-label">
                Claimed value
            </div>

            <div class="conflict-value">
                {value}
            </div>

            <div class="conflict-summary">
                {text[:160]}{"…" if len(text) > 160 else ""}
            </div>

        </div>
        """
    )


def render_conflict_comparison(conflicts):
    """
    Render up to two conflicting claims side by side with a clear
    divider between them, so the mismatch is immediately visible.
    """

    pair = conflicts[:2]

    if len(pair) == 2:
        left, right = pair

        render_html('<div class="conflict-row">')

        columns = st.columns([1, 0.18, 1])

        with columns[0]:
            render_conflict_card(left)

        with columns[1]:
            render_html(
                """
                <div class="conflict-divider">
                    <div class="conflict-divider-badge">VS</div>
                </div>
                """
            )

        with columns[2]:
            render_conflict_card(right)

        render_html('</div>')

    else:
        for item in pair:
            render_conflict_card(item)

    render_html(
        """
        <div class="conflict-callout">
            These sources disagree on the same rule. Verify the
            authoritative source before relying on either value.
        </div>
        """
    )


# ============================================================
# HEADER
# ============================================================

render_html(
    """
    <div class="brand">
        <div class="brand-icon">📘</div>
        <div class="brand-title">Rulebook AI</div>
    </div>

    <div class="subtitle">
        Ask about academic regulations and get answers grounded
        in the rulebook corpus — with evidence you can verify.
    </div>
    """
)


# ============================================================
# QUESTION INPUT
# ============================================================

render_html(
    '<div class="question-label">Ask your regulation question</div>'
)

question = st.text_area(
    label="Question",
    label_visibility="collapsed",
    placeholder=(
        "e.g. What is the minimum attendance required "
        "for a regular student?"
    ),
    height=105,
)


ask = st.button(
    "🔍  Ask Rulebook",
    type="primary",
    use_container_width=True,
)


# ============================================================
# PROCESS QUESTION
# ============================================================

if ask:

    if not question.strip():

        st.warning(
            "Please enter a question first."
        )

    else:

        with st.spinner(
            "Searching the rulebook..."
        ):

            result = detector.detect(
                question.strip()
            )

        state = result.get(
            "state",
            "UNKNOWN",
        )

        evidence = result.get(
            "evidence",
            [],
        )

        conflicts = result.get(
            "conflicts",
            [],
        )

        render_state_banner(state)


        # ====================================================
        # ANSWERABLE
        # ====================================================

        if state == "ANSWERABLE":

            render_html(
                '<div class="section-heading">Answer</div>'
)

            if evidence:

                answer_text = clean_text(
                    evidence[0].get(
                        "text",
                        "",
                    )
                )

                render_html(
                    f'<div class="answer-card">{answer_text}</div>'
)

                render_html(
                    '<div class="section-heading">📚 Supporting evidence</div>'
)

                render_html(
                    '<div class="section-description">'
                    'The strongest passages supporting this answer.'
                    '</div>'
)

                for item in evidence[:2]:

                    render_evidence(
                        item,
                        expanded=True,
                    )

            else:

                render_html(
                    '<div class="answer-card answer-empty">'
                    'The rulebook supports this question, but no '
                    'evidence passage was returned.'
                    '</div>'
)


        # ====================================================
        # NOT COVERED
        # ====================================================

        elif state == "NOT_COVERED":

            render_html(
                '<div class="section-heading">No answer inferred</div>'
)

            render_html(
                """
                <div class="not-covered-card">
                    I couldn't find sufficient information in the
                    rulebook corpus to answer this question.
                    <br>
                    <span class="not-covered-note">
                        No information from outside the corpus was used.
                    </span>
                </div>
                """
            )

            if evidence:

                render_html(
                    '<div class="section-heading">📚 Relevant passages</div>'
                )

                render_html(
                    '<div class="section-description">'
                    'These passages were retrieved, but they do not '
                    'establish the requested fact.'
                    '</div>'
)

                for item in evidence[:2]:

                    render_evidence(
                        item,
                        expanded=False,
                    )


        # ====================================================
        # CONTRADICTION
        # ====================================================

        elif state == "CONTRADICTION":

            render_html(
                '<div class="section-heading">Conflicting rules</div>'
)

            render_html(
                '<div class="section-description">'
                'Different sources state incompatible values for '
                'the same rule.'
                '</div>'
)


            # ------------------------------------------------
            # CONFLICT COMPARISON
            # ------------------------------------------------

            if conflicts:

                render_conflict_comparison(conflicts)


                # --------------------------------------------
                # Source passages
                # --------------------------------------------

                render_html(
                    '<div class="section-heading">Source passages</div>'
)

                render_html(
                    '<div class="section-description">'
                    'The original passages used to identify the conflict.'
                    '</div>'
)

                for index, item in enumerate(
                    conflicts[:2],
                    start=1,
                ):

                    name = source_name(item)

                    with st.expander(
                        f"View source passage · {name}",
                        expanded=False,
                    ):

                        render_source_passage(
                            item
                        )


            else:

                st.warning(
                    "A contradiction was detected, but the "
                    "conflicting passages were not returned."
                )


            # ------------------------------------------------
            # Additional evidence
            # ------------------------------------------------

            conflict_ids = {
                item.get("chunk_id")
                for item in conflicts
            }

            remaining = [
                item
                for item in evidence
                if item.get("chunk_id")
                not in conflict_ids
            ]

            if remaining:

                with st.expander(
                    "View additional retrieved evidence"
                ):

                    for item in remaining[:3]:

                        render_evidence(
                            item,
                            expanded=False,
                        )


        # ====================================================
        # UNKNOWN
        # ====================================================

        else:

            st.error(
                "The system returned an unexpected state."
            )


# ============================================================
# FOOTER
# ============================================================

render_html(
    """
    <div class="footer">
        Rulebook AI · Evidence-grounded academic regulation assistant
    </div>
    """
)