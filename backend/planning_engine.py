import os
import json
import random
from dataclasses import dataclass, field, asdict, is_dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Union

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

# ------------------------------------------------------------
# LLM Wrapper using LangChain's ChatGroq
# ------------------------------------------------------------



load_dotenv()

class LargeLangModel:
    """
    LLM wrapper that tries Groq first and falls back to OpenAI if Groq fails.
    """

    def __init__(
        self,
        groq_model: str = "openai/gpt-oss-120b",
        openai_model: str = "gpt-4.1-mini",
        groq_api_key: Optional[str] = None,
        openai_api_key: Optional[str] = None,
    ):

        # API KEYS
        self.groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        # MODELS
        self.groq_model = groq_model
        self.openai_model = openai_model

        # Initialize clients
        if self.groq_api_key:
            self.groq_llm = ChatGroq(model=self.groq_model, groq_api_key=self.groq_api_key)
        else:
            self.groq_llm = None

        if self.openai_api_key:
            self.openai_llm = ChatOpenAI(model=self.openai_model, api_key=self.openai_api_key)
        else:
            self.openai_llm = None

    # ------------------------------------------------------------------
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """
        Try Groq first. If it fails or doesn't exist, fallback to OpenAI.
        """
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # ----------------------
        # TRY GROQ FIRST
        # ----------------------
        if self.groq_llm:
            try:
                response = self.groq_llm.invoke(messages)
                return response.content.strip()
            except Exception as e:
                print(f"[Groq Failed → Trying OpenAI] Error: {e}")

        # ----------------------
        # FALLBACK TO OPENAI
        # ----------------------
        if self.openai_llm:
            try:
                response = self.openai_llm.invoke(messages)
                return response.content.strip()
            except Exception as e:
                print(f"[OpenAI Failed] Error: {e}")

        raise RuntimeError("Both Groq and OpenAI failed or are not configured.")


# ------------------------------------------------------------
# Data model
# ------------------------------------------------------------

@dataclass
class Persona:
    username: str
    info: str


@dataclass
class CompanyInfo:
    description: str


@dataclass
class Post:
    post_id: str
    subreddit: str
    author: str
    title: str
    body: str
    query: str


@dataclass
class Comment:
    comment_id: str
    post_id: str
    parent_comment_id: Optional[str]
    author: str
    text: str


@dataclass
class ConversationState:
    """
    LangGraph state for one Reddit-style thread.
    """
    company_info: CompanyInfo
    personas: List[Persona]
    subreddit: str
    query: str
    seed_username: str
    post_id: str
    max_comments: int = 6

    post: Optional[Post] = None
    comments: List[Comment] = field(default_factory=list)
    turn: int = 0


# ------------------------------------------------------------
# Utility: safe convert dataclass ↦ dict
# ------------------------------------------------------------

def to_dict(obj: Any) -> Any:
    """
    Convert dataclasses (recursively) to dicts; leave dicts/other types as-is.
    """
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, list):
        return [to_dict(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj


# ------------------------------------------------------------
# Prompt builders
# ------------------------------------------------------------

def build_post_prompt(state: ConversationState) -> str:
    persona = next(p for p in state.personas if p.username == state.seed_username)

    return f"""
Write a natural Reddit post for r/{state.subreddit}.
Persona background:
{persona.info}

Do not mention you are an AI or language model. No em-dashes (—).
Also do not mention your background in very detail but only use it to inform your tone and style.

Topic search query: "{state.query}"

Requirements:
- Write a catchy human-sounding Reddit TITLE and multi-paragraph BODY.
- Body should mention Slideforge in a non-salesy, natural way.
- Include situation, context, questions, frustrations, etc.
- Sound like a real Reddit user.

Return exactly this format:

TITLE: <title>
BODY:
<body text>
"""


def parse_post_response(text: str):
    upper = text.upper()
    if "TITLE:" in upper and "BODY:" in upper:
        t = upper.index("TITLE:")
        b = upper.index("BODY:")
        title = text[t + len("TITLE:"):b].strip()
        body = text[b + len("BODY:"):].strip()
        return title, body
    # Fallback if formatting isn't perfect
    lines = text.strip().split("\n", 1)
    title = lines[0][:80]
    body = text
    return title, body


def build_comment_prompt(
    state: ConversationState,
    persona: Persona,
    parent: Optional[Comment],
):
    post_text = ""
    if state.post:
        post_text = f"POST TITLE: {state.post.title}\nPOST BODY: {state.post.body}"

    recent_comments = ""
    if state.comments:
        rendered = []
        for c in state.comments[-3:]:
            rendered.append(f"{c.author} (comment {c.comment_id}): {c.text}")
        recent_comments = "\n".join(rendered)

    parent_section = ""
    if parent:
        parent_section = (
            f"\nYou are replying directly to {parent.author}'s comment "
            f"(id {parent.comment_id}):\n{parent.text}\n"
        )

    system_msg = f"""
You are roleplaying as Reddit user "{persona.username}".
Use their personality and background authentically:
{persona.info}. Do not mention you are an AI or language model.
Also do not mention your background in very detail but only use it to inform your tone and style.

Stay casual, human, conversational. No em-dashes (—).
Avoid marketing tone.
"""

    user_msg = f"""
Thread info:
{post_text}

Recent comments:
{recent_comments}

{parent_section}

Write a single 2–5 sentence Reddit comment from {persona.username}.
Do NOT use markdown. Keep it natural.
Mention Slideforge organically when relevant.

You are generating ONE new Reddit-style comment. No em-dashes (—).

Rules:
- DO NOT repeat or rephrase ANY previous comment.
- DO NOT include quotes of earlier comments.
- DO NOT generate multiple messages.
- ONLY produce a single new comment as the next reply.
Return ONLY the comment text — no metadata, no explanations.
"""

    return system_msg, user_msg


# ------------------------------------------------------------
# LangGraph Nodes
# ------------------------------------------------------------

def post_node(state: ConversationState, llm: LargeLangModel) -> ConversationState:
    """
    First node: generate the main Reddit post.
    """
    system_prompt = "You are good at writing natural, non-salesy Reddit posts."
    user_prompt = build_post_prompt(state)

    raw = llm.complete(system_prompt, user_prompt)
    title, body = parse_post_response(raw)

    state.post = Post(
        post_id=state.post_id,
        subreddit=state.subreddit,
        author=state.seed_username,
        title=title,
        body=body,
        query=state.query,
    )
    return state


def comment_node(state: ConversationState, llm: LargeLangModel) -> ConversationState:
    """
    Add one new comment to the thread.
    """
    persona = random.choice(state.personas)

    possible_parents: List[Optional[Comment]] = [None] + state.comments
    parent = random.choice(possible_parents)

    system_prompt, user_prompt = build_comment_prompt(state, persona, parent)
    text = llm.complete(system_prompt, user_prompt)

    cid = f"C{len(state.comments) + 1}"
    parent_id = parent.comment_id if parent else None

    new_comment = Comment(
        comment_id=cid,
        post_id=state.post_id,
        parent_comment_id=parent_id,
        author=persona.username,
        text=text,
    )

    state.comments.append(new_comment)
    state.turn += 1
    return state


def router_node(state: ConversationState) -> str:
    """
    Decide whether to continue generating comments or stop.
    """
    if state.turn >= state.max_comments:
        return END
    return "comment"


# ------------------------------------------------------------
# Build conversation graph
# ------------------------------------------------------------

def build_conversation_graph(llm: LargeLangModel):
    """
    Wire up LangGraph for a single Reddit-style thread.
    """

    graph = StateGraph(ConversationState)

    graph.add_node("post", lambda s: post_node(s, llm))
    graph.add_node("comment", lambda s: comment_node(s, llm))

    graph.set_entry_point("post")
    graph.add_edge("post", "comment")

    graph.add_conditional_edges(
        "comment",
        router_node,
        {"comment": "comment", END: END},
    )

    return graph.compile()


# ------------------------------------------------------------
# Calendar generation
# ------------------------------------------------------------

def generate_conversation_calendar(
    config: Dict[str, Any],
    llm: Optional[LargeLangModel] = None,
    start_date: Optional[date] = None,
    max_comments_per_thread: int = 6,
) -> List[Dict[str, Any]]:

    if llm is None:
        llm = LargeLangModel()

    if start_date is None:
        start_date = date.today()

    personas = [Persona(**p) for p in config["personas"]]
    company_info = CompanyInfo(description=config["company_info"]["description"])
    keywords = [k["keyword"] for k in config["keywords"]]
    subreddits = config["subreddits"]
    posts_per_week = config["posts_per_week"]

    random.shuffle(keywords)
    queries = keywords[:posts_per_week]

    graph = build_conversation_graph(llm)

    schedule: List[Dict[str, Any]] = []

    for idx, query in enumerate(queries, start=1):
        post_id = f"P{idx}"
        author = random.choice(personas).username
        subreddit = random.choice(subreddits)

        init_state = ConversationState(
            company_info=company_info,
            personas=personas,
            subreddit=subreddit,
            query=query,
            seed_username=author,
            post_id=post_id,
            max_comments=max_comments_per_thread,
        )

        # LangGraph may return a dataclass or a dict depending on wiring/version
        result_state: Union[ConversationState, Dict[str, Any]] = graph.invoke(init_state)

        if isinstance(result_state, dict):
            # dict-style state
            post_obj = result_state.get("post")
            comments_obj = result_state.get("comments", [])
        else:
            # dataclass-style state
            post_obj = result_state.post
            comments_obj = result_state.comments

        schedule.append(
            {
                "date": str(start_date + timedelta(days=idx - 1)),
                "subreddit": subreddit,
                "post": to_dict(post_obj),
                "comments": to_dict(comments_obj),
            }
        )

    return schedule


# ------------------------------------------------------------
# CLI Runner
# ------------------------------------------------------------

def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python planning_engine.py data.json")
        sys.exit(1)

    cfg = load_config(sys.argv[1])
    calendar = generate_conversation_calendar(cfg)

    # ---- SAVE TO JSON FILE ----
    output_path = "conversation_output.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(calendar, f, indent=4, ensure_ascii=False)

    print(f"\nSaved JSON output to: {output_path}")

    # Optional: still print a preview to terminal
    for day in calendar:
        print("\n============================")
        print(day["date"], "|", day["subreddit"])
        post = day["post"]
        print("Post:", post["title"])
        print("Author:", post["author"])
        print("Query:", post["query"])

