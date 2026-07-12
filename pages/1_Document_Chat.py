import re
from typing import BinaryIO

import streamlit as st
from docx import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from pypdf import PdfReader


st.set_page_config(
    page_title="Document Chat",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Travel Document RAG Chatbot")
st.write(
    "Upload a PDF, DOCX or TXT document and ask questions "
    "based only on its content."
)


def extract_text(uploaded_file: BinaryIO, filename: str) -> str:
    """Extract text from PDF, DOCX or TXT files."""
    filename = filename.lower()
    uploaded_file.seek(0)

    if filename.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pages = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages.append(page_text)

        return "\n".join(pages)

    if filename.endswith(".docx"):
        document = Document(uploaded_file)
        return "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    if filename.endswith(".txt"):
        return uploaded_file.read().decode(
            "utf-8",
            errors="ignore",
        )

    raise ValueError("Unsupported document format.")


def split_into_chunks(
    text: str,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> list[str]:
    """Divide a long document into overlapping text chunks."""
    cleaned_text = re.sub(r"\s+", " ", text).strip()

    if not cleaned_text:
        return []

    chunks = []
    start = 0

    while start < len(cleaned_text):
        end = start + chunk_size
        chunk = cleaned_text[start:end]
        chunks.append(chunk)

        if end >= len(cleaned_text):
            break

        start = end - overlap

    return chunks


def tokenize(text: str) -> set[str]:
    """Convert text into searchable lowercase words."""
    return set(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def retrieve_chunks(
    question: str,
    chunks: list[str],
    number_of_chunks: int = 3,
) -> list[str]:
    """Retrieve chunks containing words related to the question."""
    question_words = tokenize(question)
    scored_chunks = []

    for chunk in chunks:
        chunk_words = tokenize(chunk)
        matching_words = question_words.intersection(chunk_words)
        score = len(matching_words)

        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    relevant_chunks = [
        chunk
        for score, chunk in scored_chunks[:number_of_chunks]
        if score > 0
    ]

    if not relevant_chunks:
        return chunks[:number_of_chunks]

    return relevant_chunks


def get_secret(name: str, default: str = "") -> str:
    """Read a Streamlit secret safely."""
    try:
        return str(st.secrets[name])
    except Exception:
        return default


uploaded_file = st.file_uploader(
    "Upload a travel document",
    type=["pdf", "docx", "txt"],
)

if "document_messages" not in st.session_state:
    st.session_state.document_messages = []

for message in st.session_state.document_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

question = st.chat_input(
    "Ask a question about the uploaded document"
)

if question:
    if uploaded_file is None:
        st.error("Please upload a document first.")

    else:
        try:
            document_text = extract_text(
                uploaded_file,
                uploaded_file.name,
            )

            chunks = split_into_chunks(document_text)

            if not chunks:
                st.error(
                    "No readable text was found in the document."
                )
                st.stop()

            relevant_chunks = retrieve_chunks(
                question,
                chunks,
            )

            context = "\n\n---\n\n".join(relevant_chunks)

            api_key = get_secret("GEMINI_API_KEY")
            model_name = get_secret(
                "GEMINI_MODEL",
                "gemini-2.5-flash",
            )

            if not api_key:
                st.error(
                    "Gemini API key is missing. Add it to "
                    ".streamlit/secrets.toml."
                )
                st.stop()

            prompt = f"""
You are a document question-answering assistant.

Answer the user's question only from the supplied document context.
If the answer is not present, say:
"The uploaded document does not contain that information."

Document context:
{context}

User question:
{question}

Give a clear and simple answer.
"""

            with st.chat_message("user"):
                st.markdown(question)

            with st.chat_message("assistant"):
                with st.spinner("Searching the document..."):
                    llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        google_api_key=api_key,
                        temperature=0,
                    )

                    response = llm.invoke(prompt)
                    answer = str(response.content)

                    st.markdown(answer)

                    with st.expander(
                        "View retrieved document sections"
                    ):
                        for index, chunk in enumerate(
                            relevant_chunks,
                            start=1,
                        ):
                            st.write(
                                f"**Retrieved section {index}**"
                            )
                            st.write(chunk)

            st.session_state.document_messages.extend(
                [
                    {
                        "role": "user",
                        "content": question,
                    },
                    {
                        "role": "assistant",
                        "content": answer,
                    },
                ]
            )

        except Exception as error:
            st.error(f"Unable to process the document: {error}")