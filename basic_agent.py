import logging
from typing import AsyncIterable, Optional

from dotenv import load_dotenv
from livekit import rtc

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    ModelSettings,
    RunContext,
    cli,
    metrics,
    room_io,
    stt,
)
from livekit.agents.llm import function_tool
from livekit.plugins import azure, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# uncomment to enable Krisp background voice/noise cancellation
# from livekit.plugins import noise_cancellation

logger = logging.getLogger("basic-agent")

load_dotenv()

# Configurable list of filler words to ignore during agent speech
FILLER_WORDS = {
    "umm",
    "uh",
    "um",
    "like",
    "you know",
    "so",
    "well",
    "haan",
    "hmm",
    "hm",
    "ah",
    "er",
    "erm",
    "ok",
    "ahhh",
    "hmmm",
    "eh",
    "ehh",
    "uhh",
    "acha"
}


def is_only_filler_words(text: str) -> bool:
    """
    Check if the text contains only filler words.

    Args:
        text: The transcribed text to check

    Returns:
        True if text contains only filler words, False otherwise
    """
    if not text:
        return True

    # Normalize the text
    text_lower = text.lower().strip()

    # Remove common punctuation
    text_clean = text_lower.replace(".", "").replace(",", "").replace("?", "").replace("!", "")

    # Split into words
    words = text_clean.split()

    if not words:
        return True

    # Check if all words are filler words
    for word in words:
        if word not in FILLER_WORDS:
            # Found a real word - not just filler
            return False

    # All words are filler words
    logger.info(f"🛑 Detected only filler words: '{text}' - will be filtered")
    return True


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You would interact with users via voice."
            "with that in mind keep your responses concise and to the point."
            "do not use emojis, asterisks, markdown, or other special characters in your responses."
            "You are curious and friendly, and have a sense of humor."
            "you will speak english to the user",
        )

    async def on_enter(self):
        # when the agent is added to the session, it'll generate a reply
        # according to its instructions
        self.session.generate_reply()

    async def stt_node(
        self, audio: AsyncIterable[rtc.AudioFrame], model_settings: ModelSettings
    ) -> Optional[AsyncIterable[stt.SpeechEvent]]:
        """
        Override the STT node to filter out filler words when agent is speaking.
        This prevents filler words like "umm", "hmm" from interrupting the agent.
        """

        async def filter_filler_words():
            """Filter speech events that contain only filler words."""
            async for event in Agent.default.stt_node(self, audio, model_settings):
                # Only filter if we have text to check
                if isinstance(event, stt.SpeechEvent):
                    if event.type == stt.SpeechEventType.INTERIM_TRANSCRIPT:
                        # For interim transcripts, check if it's only filler words
                        if is_only_filler_words(event.alternatives[0].text):
                            logger.debug(f"Filtered interim filler: '{event.alternatives[0].text}'")
                            # Skip this event - don't yield it
                            continue

                    elif event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                        # For final transcripts, check if it's only filler words
                        if is_only_filler_words(event.alternatives[0].text):
                            logger.info(f"✅ Filtered final filler: '{event.alternatives[0].text}' - agent continues")
                            # Skip this event - don't yield it
                            continue

                # Not a filler word event, yield it normally
                yield event

        return filter_filler_words()

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    @function_tool
    async def lookup_weather(
        self, context: RunContext, location: str, latitude: str, longitude: str
    ):
        """Called when the user asks for weather related information.
        Ensure the user's location (city or region) is provided.
        When given a location, please estimate the latitude and longitude of the location and
        do not ask the user for them.

        Args:
            location: The location they are asking for
            latitude: The latitude of the location, do not ask user for it
            longitude: The longitude of the location, do not ask user for it
        """

        logger.info(f"Looking up weather for {location}")

        return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        # Azure STT with English and Hindi language support
        stt=azure.STT(language=["en-US", "hi-IN"]),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm="openai/gpt-4.1-mini",
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
        # Allow interruptions - filler words will be filtered in the stt_node
        allow_interruptions=True,
        # Resume if false interruption detected (no transcribed speech)
        resume_false_interruption=True,
        false_interruption_timeout=2.0,
        # Require at least 2 words to interrupt (helps filter single filler words)
        min_interruption_words=2,
    )

    # log metrics as they are emitted, and total usage after session is over
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    # shutdown callbacks are triggered when the session is over
    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=MyAgent(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                # uncomment to enable the Krisp BVC noise cancellation
                # noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
