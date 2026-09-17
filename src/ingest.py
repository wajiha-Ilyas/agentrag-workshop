"""Loads documents from data/docs/, chunks them, embeds them, and persists to Chroma.

Run standalone to (re)build the vector store:
    python -m src.ingest
"""

import os

from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "docs")
PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".chroma")
COLLECTION_NAME = "agentrag_docs"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)


def load_documents(data_dir: str = DATA_DIR):
    docs = []

    md_txt_loader = DirectoryLoader(
        data_dir,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
    )
    docs.extend(md_txt_loader.load())

    txt_loader = DirectoryLoader(
        data_dir,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
    )
    docs.extend(txt_loader.load())

    pdf_loader = DirectoryLoader(
        data_dir,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,
        show_progress=False,
    )
    docs.extend(pdf_loader.load())

    return docs


def build_vectorstore(data_dir: str = DATA_DIR, persist_dir: str = PERSIST_DIR) -> Chroma:
    documents = load_documents(data_dir)
    if not documents:
        raise ValueError(f"No documents found in {data_dir}. Add .md/.txt/.pdf files first.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(documents)

    embeddings = get_embeddings()
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=persist_dir,
    )
    return vectorstore


def load_vectorstore(persist_dir: str = PERSIST_DIR) -> Chroma:
    embeddings = get_embeddings()
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


if __name__ == "__main__":
    print(f"Loading documents from {DATA_DIR} ...")
    vs = build_vectorstore()
    print(f"Ingested and persisted to {PERSIST_DIR}")

    query = "What is an AI agent?"
    results = vs.similarity_search(query, k=3)
    print(f"\nSanity check — top {len(results)} chunks for: {query!r}\n")
    for i, doc in enumerate(results, start=1):
        source = doc.metadata.get("source", "unknown")
        print(f"[{i}] source={source}")
        print(doc.page_content[:200].replace("\n", " ") + "...")
        print()
