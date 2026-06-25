import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    PdfReader = None
    PdfWriter = None


class DropArea(QFrame):
    def __init__(self, on_pdf_dropped):
        super().__init__()
        self.on_pdf_dropped = on_pdf_dropped
        self.setAcceptDrops(True)
        self.setObjectName("dropArea")

        layout = QVBoxLayout(self)
        self.label = QLabel("Drag and drop PDF file here")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = Path(url.toLocalFile())
            if file_path.suffix.lower() == ".pdf":
                self.on_pdf_dropped(file_path)
                event.acceptProposedAction()
                return
        event.ignore()


class PdfSplitterWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.selected_pdf = None
        self.page_count = 0

        self.setWindowTitle("PDF Range Splitter")
        self.resize(620, 430)

        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        self.drop_area = DropArea(self.set_pdf)
        layout.addWidget(self.drop_area)

        pick_row = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setReadOnly(True)
        self.path_input.setPlaceholderText("Selected PDF will appear here")

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_pdf)

        pick_row.addWidget(self.path_input, 1)
        pick_row.addWidget(browse_button)
        layout.addLayout(pick_row)

        self.info_label = QLabel("Page count: No PDF selected")
        layout.addWidget(self.info_label)

        layout.addWidget(QLabel("Ranges"))

        self.ranges_input = QTextEdit()
        self.ranges_input.setPlaceholderText(
            "Example: 1-3 , 5-17"
        )
        layout.addWidget(self.ranges_input, 1)

        split_button = QPushButton("Create PDFs")
        split_button.clicked.connect(self.split_pdf)
        layout.addWidget(split_button)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        self.setStyleSheet(
            """
            QWidget {
                font-size: 14px;
            }
            #dropArea {
                border: 2px dashed #777;
                border-radius: 8px;
                min-height: 95px;
                background: #f7f7f7;
            }
            QPushButton {
                padding: 8px 12px;
            }
            QTextEdit, QLineEdit {
                padding: 7px;
            }
            """
        )

    def browse_pdf(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF",
            "",
            "PDF Files (*.pdf)",
        )
        if file_name:
            self.set_pdf(Path(file_name))

    def set_pdf(self, file_path):
        if PdfReader is None:
            self.show_error(
                "Missing library",
                "pypdf is not installed. Run this command in the terminal:\n\n"
                "pip install PyQt6 pypdf",
            )
            return

        try:
            reader = PdfReader(str(file_path))
            self.page_count = len(reader.pages)
        except Exception as error:
            self.show_error("Could not read PDF", str(error))
            return

        self.selected_pdf = file_path
        self.path_input.setText(str(file_path))
        self.info_label.setText(f"Page count: {self.page_count}")
        self.status_label.setText("")

    def parse_ranges(self):
        text = self.ranges_input.toPlainText().replace(",", "\n")
        ranges = []

        for line in text.splitlines():
            item = line.strip()
            if not item:
                continue

            if "-" in item:
                parts = item.split("-", 1)
                if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                    raise ValueError(f"Invalid range: {item}")
                start = int(parts[0].strip())
                end = int(parts[1].strip())
            else:
                start = int(item)
                end = start

            if start < 1 or end < 1:
                raise ValueError("Page numbers must be 1 or greater.")
            if start > end:
                raise ValueError(f"Start cannot be greater than end: {item}")
            if end > self.page_count:
                raise ValueError(
                    f"Range {item} exceeds the PDF page count. "
                    f"This PDF has {self.page_count} pages."
                )

            ranges.append((start, end))

        if not ranges:
            raise ValueError("You must enter at least one range.")

        return ranges

    def split_pdf(self):
        if PdfReader is None:
            self.show_error(
                "Missing library",
                "pypdf is not installed. Run this command in the terminal:\n\n"
                "pip install PyQt6 pypdf",
            )
            return

        if not self.selected_pdf:
            self.show_error("No PDF selected", "Please select or drag and drop a PDF file first.")
            return

        try:
            ranges = self.parse_ranges()
        except ValueError as error:
            self.show_error("Range error", str(error))
            return

        try:
            reader = PdfReader(str(self.selected_pdf))
            output_dir = self.selected_pdf.parent
            base_name = self.selected_pdf.stem

            created_files = []
            for start, end in ranges:
                writer = PdfWriter()

                for page_index in range(start - 1, end):
                    writer.add_page(reader.pages[page_index])

                output_path = output_dir / f"{base_name} ({start}-{end}).pdf"
                with output_path.open("wb") as output_file:
                    writer.write(output_file)

                created_files.append(output_path.name)

        except Exception as error:
            self.show_error("Splitting error", str(error))
            return

        self.status_label.setText(f"{len(created_files)} PDFs created.")
        QMessageBox.information(
            self,
            "Completed",
            "PDFs have been saved to the source file's directory:\n\n"
            + "\n".join(created_files),
        )

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)


def main():
    app = QApplication(sys.argv)
    window = PdfSplitterWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()