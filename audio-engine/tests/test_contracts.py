from inspect import isabstract

from tunemorph_audio import AudioTranscriber, PreviewRenderer, SourceSeparator, StyleTransformer


def test_pipeline_boundaries_are_abstract() -> None:
    assert all(
        isabstract(contract)
        for contract in (AudioTranscriber, PreviewRenderer, SourceSeparator, StyleTransformer)
    )
