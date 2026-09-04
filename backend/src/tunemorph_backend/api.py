from fastapi import APIRouter, HTTPException

from .schemas import StyleSummary

router = APIRouter(prefix="/api")

STYLES = (
    StyleSummary(
        id="original",
        name="Original",
        description="Preserve the transcription's structure.",
        icon="waveform",
    ),
    StyleSummary(
        id="music_box",
        name="Music Box",
        description="Bright melody and delicate mechanical arpeggios.",
        icon="sparkles",
    ),
    StyleSummary(
        id="solo_piano",
        name="Solo Piano",
        description="Playable two-hand piano voicings.",
        icon="piano",
    ),
    StyleSummary(
        id="eight_bit",
        name="8-Bit",
        description="Tight quantisation and limited chiptune voices.",
        icon="gamepad",
    ),
    StyleSummary(
        id="lullaby",
        name="Lullaby",
        description="Soft dynamics and a calmer arrangement.",
        icon="moon",
    ),
)


@router.get("/styles", response_model=list[StyleSummary], tags=["styles"])
async def list_styles() -> tuple[StyleSummary, ...]:
    return STYLES


@router.get("/styles/{style_id}", response_model=StyleSummary, tags=["styles"])
async def get_style(style_id: str) -> StyleSummary:
    try:
        return next(style for style in STYLES if style.id == style_id)
    except StopIteration as error:
        raise HTTPException(status_code=404, detail="Style not found") from error
