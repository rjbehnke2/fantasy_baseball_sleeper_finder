"""Prompt templates for AI scouting reports.

Defines the system prompt and report-type-specific user prompts that guide
Claude to generate grounded, actionable fantasy baseball analysis.
"""

SYSTEM_PROMPT = """You are an elite fantasy baseball analyst specializing in dynasty and \
auction leagues. You have deep expertise in Statcast data, advanced metrics, aging curves, \
and player development. Your analysis is data-driven, authoritative, and actionable.

CRITICAL RULES:
1. ONLY reference statistics and scores provided in the player context below. Never invent \
or hallucinate stats.
2. Write in an authoritative but accessible tone — like a trusted league-mate who's done \
the homework.
3. Always frame analysis through a dynasty auction lens: What is this player worth? Is he \
a buy, sell, or hold? How does his age and trajectory affect his long-term value?
4. Be specific with dollar values and surplus calculations when provided.
5. Acknowledge uncertainty — use confidence levels, qualifying language when metrics conflict.
6. Keep it concise and impactful. Every sentence should add value.
"""

FULL_REPORT_TEMPLATE = """Generate a comprehensive scouting report for the following player. \
Use ONLY the data provided below — do not reference any information not included here.

{player_context}

Write the report with these exact sections:

## Headline Assessment
One to two sentences: the key takeaway. Include a clear BUY / SELL / HOLD recommendation \
with conviction level (high/medium/low).

## The Case For
One paragraph: What the underlying data says in the player's favor. Reference specific \
Statcast metrics, trend improvements, favorable age position, or undervaluation signals. \
Write as a narrative, not a stat dump.

## The Case Against
One paragraph: Risk factors. Reference regression signals, injury concerns, declining \
trends, age-related concerns, or overvaluation indicators. Be honest about weaknesses.

## Dynasty Outlook
One paragraph: Multi-year trajectory analysis. Where is this player on his career arc? \
What does the 3-year outlook look like? Is he a cornerstone to build around, a sell-high \
candidate, or a buy-low opportunity?

## Auction Verdict
One to two sentences: Specific dollar value recommendation based on the projected auction \
value and surplus calculations provided. Frame it in terms of what you'd pay in a dynasty \
auction."""

SLEEPER_SPOTLIGHT_TEMPLATE = """Generate a sleeper spotlight report for the following player. \
This player has been identified by our models as significantly undervalued. Use ONLY the \
data provided below.

{player_context}

Write the report with these exact sections:

## The Hidden Gem
Two to three sentences: Why this player is being overlooked and what the models see that \
the market doesn't. Reference the specific undervaluation signals.

## The Statcast Story
One paragraph: What the advanced metrics reveal about this player's true talent level. \
Focus on the gap between expected and actual performance, batted ball quality, and plate \
discipline trends.

## Dynasty Buy Window
One to two sentences: Why now is the time to acquire this player in a dynasty league, \
and what you should be willing to pay."""

BUST_WARNING_TEMPLATE = """Generate a bust warning report for the following player. \
Our models have flagged significant regression risk. Use ONLY the data provided below.

{player_context}

Write the report with these exact sections:

## Warning Signs
Two to three sentences: The key red flags that suggest this player is overvalued. \
Be specific about which metrics are unsustainable.

## The Regression Case
One paragraph: Detailed analysis of why regression is likely. Reference specific luck \
indicators (BABIP, LOB%, HR/FB%), declining trends, or age-related concerns.

## Dynasty Sell Signal
One to two sentences: Recommendation on whether to sell high in dynasty, and what you \
might realistically get in return."""

DYNASTY_OUTLOOK_TEMPLATE = """Generate a dynasty outlook report for the following player. \
Focus on long-term value and career trajectory. Use ONLY the data provided below.

{player_context}

Write the report with these exact sections:

## Career Arc Position
Two to three sentences: Where this player sits on his development/aging curve. Reference \
age, years of control, and historical comps at this career stage.

## Three-Year Projection
One paragraph: What the models project for this player over the next three seasons. \
Reference improvement/decline trends, consistency score, and age-adjusted expectations.

## Dynasty Valuation
One to two sentences: Specific dynasty value assessment — is this a cornerstone, a \
complementary piece, or a sell candidate? Include auction dollar context."""

REPORT_TEMPLATES = {
    "full": FULL_REPORT_TEMPLATE,
    "sleeper_spotlight": SLEEPER_SPOTLIGHT_TEMPLATE,
    "bust_warning": BUST_WARNING_TEMPLATE,
    "dynasty_outlook": DYNASTY_OUTLOOK_TEMPLATE,
}
