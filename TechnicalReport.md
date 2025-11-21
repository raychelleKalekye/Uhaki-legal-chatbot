# 1. Data Preprocessing

## 1.1 Overview
- The raw data was in pdf format with unnecessary formats such as headers, footers page numbers.
- Preprocessing was needed because model couldnt understand text and also context without it being formatted.

## 1.2 Steps in Preprocessing
- **Text cleaning**
  - Removed extra spaces, line breaks, and strange characters.
  - Removed headers, footers, landing page, page numbers, bold and italic formats.
  - Changed pdf format to UTF-8 econding plain text files.
  - Changed plain text files to json format

- **Structuring the data**
  - Changed json files to chunks using chapter and section number.
  - Linked chunks to previous and next chunks.

- **Embedding data**
- Changed text in json files to embeddings using intfloat/e5 model.

- **Storing data**
- Stored data in chroma vector database using the following attributes:
   act – The name of the Act from which this text is extracted.
   part - The structural division within the act
   section - the full section label exactly as it appears in the Act.
   section_number - numeric identifier of the section
   section_title - short tile of the section
   section path- navigation path showing where the chunk sits in the act hierarchy
   chunk_index - the position of this chunk within the section
   chunk_id - a unique ID assigned to the chunk within the entire corpus
   text - actual chunk content
   previous chunk ID
   next chunk ID
  
Example: {
    "act": "Constitution of Kenya",
    "part": "General",
    "section": "7 – National, official and other languages",
    "section_number": "7",
    "section_title": "National, official and other languages",
    "section_path": "General > 7",
    "chunk_index": 1,
    "chunk_id": 8,
    "text": "(1) The national language of the Republic is Kiswahili. (2) The official languages of the Republic are Kiswahili and English. (3) The State shall— (a) promote and protect the diversity of language of the people of Kenya; and (b) promote the development and use of indigenous languages, Kenyan Sign language, Braille and other communication formats and technologies accessible to persons with disabilities.",
    "prev_chunk_id": 7,
    "next_chunk_id": 9,
    "act_year": null
  },

## 1.3 Data Cleaning Results
- Data removed:
    - Kenya Gazette boilerplate (e.g. “KENYA GAZETTE SUPPLEMENT…”, printer/publisher info)
    - Cover page metadata (Act numbers, assent/commencement date blocks, signatures)
    - Page headers and footers (repeated titles, chapter labels, running heads)
    - Stand-alone page numbers and line numbers
    - Scanned/OCR artefacts (broken characters, control characters, odd symbols)
    - Excess whitespace (multiple spaces, blank lines, leading indentation)
    - Duplicated section titles from the “Arrangement of Sections” list
    - Non-substantive formatting markers (manual line breaks inside sentences, stray bullets)

- Short summary:
  - After cleaning, the dataset was more consistent and it became much easier to separate the Acts into clean sections for embedding and retrieval.

---

# 2. Model Architectures

## 2.1 Overview of the System
  - Encode the user question.
  - Receive user query from chat UI.
  - Embed user query using intfloat/e5 model.
  - Using cosine similarity, retrieve the most relevant sections from the database using query embeddings.
  - Re-rank the candidate sections using miniLM model.
  - Send query and related sections to LLM for generation of final answer.

## 2.2 Retrieval Stack (Embeddings + Vector Store)

Uhaki does not train its own retrieval model from scratch. Instead, it uses a pre-trained sentence-embedding model plus a vector database.

- **Embedding model:** `intfloat/e5-base-v2` (Sentence Transformers)
- **Input:** 
  - User questions
  - Act sections (cleaned + section-level text)
- **Output:** 
  - 768-dimensional vectors for each question and section
- **Usage in Uhaki:**
  - All Act sections are embedded once and stored in **ChromaDB**.
  - At query time, the user question is embedded.
  - We run a dense vector search over the stored section embeddings to get the most similar sections.
- **Key details:**
  - Similarity: cosine similarity on the embedding vectors.
  - Max sequence length: 512. It safely covers typical legal sections.


## 2.4 Reranker / Scoring Model

After retrieval, Uhaki uses a cross-encoder reranker to sharpen the top-20 list.

- **Type:** pre-trained cross-encoder from the `sentence-transformers` library (MS MARCO-MiniLM-v6).
- **Input:** 
  - (question, section) pairs for the top candidates from the hybrid step.
- **Output:** 
  - A single relevance score per pair.
- **Usage in Uhaki:**
  - For each candidate section in the top-20:
    - Feed `(user question, section text)` to the cross-encoder.
    - Receive a scalar relevance score.
  - Re-rank sections purely by the cross-encoder score.
  - Keep the **final top-6 sections** for answer generation (Trial-6 configuration).
  - Batch size and max sequence length follow the model defaults to keep the pipeline simple.

## 2.5 Answer Generation / Formatting

The final answer is generated by an LLM, using only the retrieved legal sections as context.

- **LLM:** `Qwen/Qwen3-8B-Instruct` (used as the base answer model in Uhaki).
- **Input to the LLM:**
  - User question.
  - The final top-6 sections (with Act names, section numbers, and headings).
- **Output from the LLM:**
  - A natural-language answer that:
    - Explains the legal position in plain language.
    - References relevant Acts and section numbers.
- **Constraints and formatting:**
  - The prompt explicitly instructs the model to:
    - Answer **only** from the provided sections where possible.
    - Avoid hallucinating Kenyan law that isn’t in the context.
    - Cite Acts/sections in a simple, readable format (e.g. “Section 33 of the County Governments Act”).
  - Post-processing:
    - Attach a short “Sources” list showing which Act sections were used.
    - Optionally log the used sections for later evaluation (retrieval metrics + manual review).

## 2.6 Training / Fine-Tuning

Uhaki mostly relies on pre-trained models and does **not** train a new retrieval or answer model from scratch.

- **Vocabulary / tokens:**
  - We use the existing tokenizer/vocabulary from:
    - `intfloat/e5-base-v2` for embeddings.
    - The cross-encoder model for reranking.
    - `Qwen/Qwen3-8B-Instruct` for answer generation.
  - No custom tokens or special markers were added.

- **Model training:**
  - Instead of gradient-based training, I:
    - Built a labelled set of Kenyan-law Q&A pairs containing questions and ground act and section.
    - Used that dataset to **evaluate** different retrieval configs (Trial-1 to Trial-6).
    - Tuned hyperparameters like:
      - number of BM25 candidates,
      - number of dense candidates,
      - hybrid fusion weights,
      - final top-6 used for the LLM.

- **Evaluation-driven tuning:**
  - For each trial, we measured:
    - Section Hit@6, Recall@6, Precision@6, and Mean Retrieval Rank for retrieval.



# 3. Evaluation Metrics

## 3.1 Retrieval Metrics
- **Hit@6**  
  - Whether the correct section appears in the top 6 results.  
  - Example: Hit@3 = 0.80 means 80% of the time the correct section is in the top 3.

- **Precision@k**  
  - Of the top 6 sections returned, how many are actually relevant.

- **Recall@6**  
  - Of all relevant sections, how many appear in the top 6.

- **MRR (Mean Reciprocal Rank)**  
  - Measures how high the correct section appears in the ranking.  
  - Higher MRR means the correct section is usually near the top.

List your main scores, for example:
- Precision@6: `0.1422` low because Precision looks low simply because we always pull 6 candidates but only have 1 relevant Act/section per question, so by definition Precision@6 is just Recall@6 divided by 6 and can never go higher than about 0.17.
- Recall@6: `0.8533`
- MRR@6: `0.7043`
**Act-level metrics**

| Trial   | Act_Precision@6 | Act_Recall@6 | MRR_act@6 |
|---------|---------|---------|-----------|
| Trial 1 |  0.1383 | 0.83    |  0.6665   |
| Trial 2 | 0.1394  | 0.8367  | 0.7008    |
| Trial 3 | 0.1133  | 0.6800  | 0.6159    |
| Trial 4 | 0.1300  | 0.7800  | 0.6162    |
| Trial 5 | **0.1422** | **0.8533** | **0.7043** |

- Trial-5 is the current best configuration and is the one used as the final version in this project.

## 3.2 Answer Quality Metrics

For response generation, the following metrics were used:

- **Semantic cosine similarity (question ↔ answer)** – measures how well the generated answer aligns with the meaning of the user’s question.
- **NLI entailment probability** – the probability (from a Natural Language Inference model) that the answer is logically entailed by the question.
- **Role match rate** – percentage of answers where the LLM correctly stays in the intended role of a Kenyan legal advisor.

On a test set of 322 Q&A pairs, Uhaki achieved:

- **Mean QA semantic similarity:** 0.89 (median 0.89)  
- **Mean NLI entailment probability:** 0.80  
- **Role match rate:** 0.96  

These scores indicate that, on average, answers are semantically close to the questions, logically consistent with them, and that the model almost always stays in the correct legal-advisor role.

## 3.3 Weaknesses and Observations
- The system works best when:
  - Questions mention clear keywords that also appear in the law text.
  - The relevant section is short and focused.

- The system struggles when:
  - Many sections share similar wording.
  - The correct answer is spread across multiple sections.

- Possible reasons:
  - Some questions do not map cleanly to a single section.

# 4. Challenges Faced

## 4.1 Data-Related Challenges

* **Challenge type:** Bad sectioning strategy

  * **Challenge itself:** Initially, sections were split based on word lengthinstead of the actual legal section boundaries.
  * **Issue:** Retrieval became terrible — chunks from the same legal section were scattered, passages didn’t correlate to the user question, and sometimes only half a legal idea appeared in the result.
  * **Solution:** Re-designed the dataset to follow the real legal structure (Act → Part → Section → Chunk). Chunks were then linked using `prev_chunk_id` and `next_chunk_id`.
  * **Impact:** Retrieval became more consistent, chunks stayed contextually related, and answers were easier to stitch together.

* **Challenge type:** Data quality

  * **Challenge itself:** Inconsistent formatting, typos, and broken text across different Acts.
  * **Issue:** This affected embedding quality and reduced ranking accuracy.
  * **Solution:** Cleaned and normalised the entire corpus and rebuilt section metadata.
  * **Impact:** Much more predictable retrieval and better Act/section extraction.

* **Challenge type:** Similar or overlapping sections

  * **Challenge itself:** Many legal sections sound similar even when they address different ideas.
  * **Issue:** Retrieval would sometimes rank a “near-miss” section higher than the genuinely relevant one.
  * **Solution:** Improved scoring logic and created extra training examples for problematic pairs.
  * **Impact:** Sharper and more accurate top-ranked results.

---

## 4.2 Model / System Challenges

* **Challenge type:** Hard-to-digest output

  * **Challenge itself:** Even after retrieval improved, the raw legal text was still too dense for users.
  * **Issue:** The system could retrieve the right section but couldn’t *explain* it clearly.
  * **Solution:** Added the Qwen LLM to summarise, simplify, and ground the final response in the retrieved chunks.
  * **Impact:** Outputs became clearer, more conversational, and easier for users to understand.

* **Challenge type:** Slow responses

  * **Challenge itself:** Reranking too many sections was expensive.
  * **Issue:** High latency, especially for long Acts like the Constitution.
  * **Solution:** Reduced the candidate pool, cached frequent queries, and optimised retrieval code.
  * **Impact:** Faster responses with no major drop in accuracy.

## 4.3 Operational / Practical Challenges

* **Challenge type:** LLM system integration

  * **Challenge itself:** Qwen was too large to run on the local machine.
  * **Issue:** The LLM couldn’t be hosted directly on the laptop, blocking backend integration.
  * **Solution:** Exposed the notebook model as an API using an **ngrok tunnel**, allowing the Visual Studio backend to call it remotely.
  * **Impact:** Full integration between retrieval (backend) and generation (Qwen in notebook) without needing a high-end GPU.

# 5. Summary

- Preprocessing and cleaning made the dataset more reliable and easier to use.  
- The retrieval architecture (embeddings + search + reranking) gives a structured way to find relevant sections.  
- Metrics like Precision@6, Recall@6, and MRR show how well the system retrieves the right sections and where it still fails.  
- Challenges in data quality, overlapping sections, and tooling were addressed with practical fixes that improved overall performance.
