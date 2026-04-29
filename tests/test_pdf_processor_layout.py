from core.modules.book_processor import ProcessingQuality
from core.modules.pdf_processor import PDFProcessorOCR


class FakePage:
    def __init__(self, payload: dict, fallback_text: str = ""):
        self.payload = payload
        self.fallback_text = fallback_text
        self.number = 0

    def get_text(self, mode="text", sort=False):
        if mode == "dict":
            return self.payload
        return self.fallback_text


def test_extract_page_text_preserving_layout_keeps_lines_and_block_separation():
    payload = {
        "blocks": [
            {
                "type": 0,
                "bbox": [40, 40, 300, 100],
                "lines": [
                    {
                        "bbox": [40, 40, 200, 55],
                        "spans": [{"text": "Capítulo I"}],
                    },
                    {
                        "bbox": [40, 58, 260, 73],
                        "spans": [{"text": "Uma linha logo abaixo"}],
                    },
                ],
            },
            {
                "type": 0,
                "bbox": [40, 120, 350, 180],
                "lines": [
                    {
                        "bbox": [40, 120, 300, 135],
                        "spans": [{"text": "Novo parágrafo após espaço vertical"}],
                    },
                    {
                        "bbox": [40, 138, 320, 153],
                        "spans": [{"text": "Continuação do parágrafo"}],
                    },
                ],
            },
        ]
    }
    page = FakePage(payload, fallback_text="fallback bruto")

    text = PDFProcessorOCR.extract_page_text_preserving_layout(page, preserve_layout=True)

    assert text == (
        "Capítulo I\n"
        "Uma linha logo abaixo\n\n"
        "Novo parágrafo após espaço vertical\n"
        "Continuação do parágrafo"
    )


def test_extract_page_text_preserving_layout_uses_sorted_text_when_layout_disabled():
    processor = PDFProcessorOCR(quality=ProcessingQuality.DRAFT)
    page = FakePage({"blocks": []}, fallback_text="texto simples")

    text = processor.extract_page_text_preserving_layout(page, preserve_layout=False)

    assert text == "texto simples"
