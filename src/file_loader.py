from typing import Union, List, Literal
import glob
from tqdm import tqdm
import multiprocessing
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def remove_non_utf8_characters(text):
    return ''.join(char for char in text if ord(char) < 128)


def load_pdf(pdf_file):
    docs = PyPDFLoader(pdf_file, extract_images=True).load()
    for doc in docs:
        doc.page_content = remove_non_utf8_characters(doc.page_content)
    return docs

# This function returns the number of CPU cores available on the machine.
# It is used to determine how many processes can be run in parallel for loading files.
def get_num_cpu():
    return multiprocessing.cpu_count()

# This is the base class for loaders
class BaseLoader:
    def __init__(self) -> None:
        self.num_processes = get_num_cpu()

    def __call__(self, files: List[str], **kwargs):
        pass

# This class is responsible for loading PDF files in parallel using multiprocessing.
class PDFLoader(BaseLoader):
    def __init__(self) -> None:
        super().__init__()

    def __call__(self, pdf_files: List[str], **kwargs):
        num_processes = min(self.num_processes, kwargs["workers"])
        with multiprocessing.Pool(processes=num_processes) as pool:
            doc_loaded = []
            total_files = len(pdf_files)
            with tqdm(total=total_files, desc="Loading PDFs", unit="file") as pbar:
                for result in pool.imap_unordered(load_pdf, pdf_files):
                    doc_loaded.extend(result)
                    pbar.update(1)
        return doc_loaded

# This class is responsible for splitting text documents into smaller chunks.
class TextSplitter:
    def __init__(
        self,
        separators: List[str] = ['\n\n', '\n', ' ', ''],
        chunk_size: int = 300,
        chunk_overlap: int = 0
    ) -> None:
        self.splitter = RecursiveCharacterTextSplitter(
            separators=separators,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def __call__(self, documents):
        return self.splitter.split_documents(documents)


class Loader:
    def __init__(
        self,
        file_type: str = Literal["pdf"],
        split_kwargs: dict = {
            "chunk_size": 300,
            "chunk_overlap": 0
        }
    ) -> None:
        assert file_type in ["pdf"], "file_type must be pdf"
        self.file_type = file_type
        if file_type == "pdf":
            self.doc_loader = PDFLoader()
        else:
            raise ValueError("file_type must be pdf")

        self.doc_splitter = TextSplitter(**split_kwargs)

    def load(self, pdf_files: Union[str, List[str]], workers: int = 1):
        if isinstance(pdf_files, str):
            pdf_files = [pdf_files]
        doc_loaded = self.doc_loader(pdf_files, workers=workers)
        doc_split = self.doc_splitter(doc_loaded)
        return doc_split

    def load_dir(self, dir_path: str, workers: int = 1):
        if self.file_type == "pdf":
            files = glob.glob(f"{dir_path}/*.pdf")
            assert len(files) > 0, f"No {self.file_type} files found in {dir_path}"
        else:
            raise ValueError("file_type must be pdf")

        return self.load(files, workers=workers)


# if __name__ == "__main__":
#     # Example usage
#     loader = Loader(file_type="pdf", split_kwargs={"chunk_size": 300, "chunk_overlap": 50})
#     documents = loader.load_dir("/root/chat-RAG-new/data", workers=4)
#     print(f"Loaded {len(documents)} documents.")
#     print(documents[0].page_content[:500])  # Print the first 500 characters of the first document