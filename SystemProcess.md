# 1. Data Preprocessing

## 1.1 Overview
- The raw data was in pdf format with unnecessary formats such as headers, footers page numbers.
- Preprocessing was needed because model couldnt understand text and also context without it being formatted

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
   [] act – The name of the Act from which this text is extracted.
Example: “Constitution of Kenya”.

part – The broader structural division within the Act.
Some Acts are divided into Parts (e.g. “General”), others can be null.

section – The full section label exactly as it appears in the Act.
Example: “7 – National, official and other languages”.

section_number – Numeric identifier of the section for easier indexing.
Example: “7”.

section_title – The short title of the section, extracted from the full section text.
Example: “National, official and other languages”.

section_path – A pre-computed navigation path showing where the chunk sits in the Act hierarchy.
Format: {Part} > {SectionNumber}.

chunk_index – The position of this chunk within the section (0-based or 1-based depending on your pipeline).
This is used for reconstructing the entire section from multiple chunks.

chunk_id – A unique ID assigned to the chunk within the entire corpus.

text – The actual chunk content.
This is what is fed into the embedding model for retrieval.

prev_chunk_id and next_chunk_id – Links that allow traversal of the Act in reading order.
Useful for stitching together multi-chunk responses and context windows.

act_year – The year the Act was passed or last revised.
Some Acts don’t explicitly include this, so it may be null.

  

## 1.3 Data Cleaning Results
- Number of records **before** cleaning: `XXX`
- Number of records **after** cleaning: `YYY`

- Data removed:
  - Duplicate entries
  - Rows with missing key fields (e.g. no question or no section)
  - Corrupted or unreadable text

- Short summary:
  - “After cleaning, the dataset is more consistent and easier for the model to learn from.”

---

# 2. Model Architectures

## 2.1 Overview of the System
- Describe the overall pipeline in simple terms, for example:
  - Encode the user question.
  - Retrieve the most relevant sections from the database.
  - (Optional) Re-rank the candidate sections.
  - (Optional) Generate or format the final answer.

## 2.2 Retrieval Model (Embeddings / Vector Search)
- **Type:** e.g. sentence transformer for embeddings.
- **Input:** text (questions and sections).
- **Output:** fixed-size vectors used for similarity search.
- **Key parameters:**
  - Embedding size: `XXX`
  - Batch size: `XXX`
  - Max sequence length: `XXX`
  - Any special preprocessing before encoding.

## 2.3 Keyword / BM25 Component (if used)
- **Role:** support the embedding model with keyword-based search.
- **Input:** question text.
- **Output:** ranked list of sections based on term matching.
- **Notes:**
  - How many top sections you keep from BM25.
  - How you combine BM25 with embeddings (e.g. weighted score).

## 2.4 Reranker / Scoring Model (if used)
- **Type:** e.g. cross-encoder.
- **Input:** (question, section) pairs.
- **Output:** relevance score.
- **Main parameters:**
  - Batch size: `XXX`
  - Max sequence length: `XXX`
  - Number of training epochs (if trained): `XXX`
  - Learning rate: `XXX`

## 2.5 Answer Generation / Formatting (if used)
- **Role:** turn retrieved sections into a final answer.
- **Input:** user question + top-k sections.
- **Output:** natural language answer or structured output.
- **Notes:**
  - Whether you constrain the answer to stay close to the retrieved text.
  - Any post-processing (e.g. highlighting sections, citations).

## 2.6 Vocabulary and Training Setup (if any models were trained)
- **Vocabulary**
  - Size of vocabulary (if relevant): `XXX`
  - Any special tokens (e.g. `[SECTION_HEAD]`, `[BODY]`).
- **Training data**
  - Number of training examples: `XXX`
  - Number of validation examples: `XXX`
- **Training process**
  - Loss function (e.g. cross-entropy, ranking loss).
  - Optimizer (e.g. Adam).
  - Number of epochs and early stopping rules.

---

# 3. Evaluation Metrics

## 3.1 Retrieval Metrics
Explain in simple language:

- **Hit@k**  
  - Whether the correct section appears in the top `k` results.  
  - Example: Hit@3 = 0.80 means 80% of the time the correct section is in the top 3.

- **Precision@k**  
  - Of the top `k` sections returned, how many are actually relevant.

- **Recall@k**  
  - Of all relevant sections, how many appear in the top `k`.

- **MRR (Mean Reciprocal Rank)**  
  - Measures how high the correct section appears in the ranking.  
  - Higher MRR means the correct section is usually near the top.

List your main scores, for example:
- Hit@1: `XX`
- Hit@3: `XX`
- Hit@6: `XX`
- Precision@6: `XX`
- Recall@6: `XX`
- MRR@6: `XX`

## 3.2 Answer Quality Metrics (if applicable)
- **Exact Match (EM)** – percentage of answers that exactly match a reference answer.
- **Similarity metrics** – e.g. BLEU, ROUGE, or a manual rating (1–5) for:
  - Correctness
  - Completeness
  - Clarity

## 3.3 Weaknesses and Observations
- The system works best when:
  - Questions mention clear keywords that also appear in the law text.
  - The relevant section is short and focused.

- The system struggles when:
  - Questions are very vague or very long.
  - Many sections share similar wording.
  - The correct answer is spread across multiple sections.

- Possible reasons:
  - Limited training data for some topics.
  - Very dense legal language.
  - Some questions do not map cleanly to a single section.

---

# 4. Challenges Faced

Describe each challenge in a simple pattern:  
**Challenge type → Challenge itself → Issue → Solution → Impact**

## 4.1 Data-Related Challenges
- **Challenge type:** Data quality  
  - **Challenge itself:** Inconsistent formatting, typos, and broken text.  
  - **Issue:** Made it hard for the model to learn and for retrieval to be accurate.  
  - **Solution:** Normalised formatting, cleaned text, removed bad rows.  
  - **Impact:** More stable results and easier debugging.

- **Challenge type:** Uneven coverage of topics  
  - **Challenge itself:** Some legal areas had many examples, others had very few.  
  - **Issue:** The system performed better on well-represented topics and worse on rare ones.  
  - **Solution:** Added more examples where possible or rebalanced the dataset.  
  - **Impact:** More consistent performance across topics.

## 4.2 Model / System Challenges
- **Challenge type:** Similar or overlapping sections  
  - **Challenge itself:** Multiple sections looked relevant to the same question.  
  - **Issue:** The model sometimes ranked a “near-miss” section above the best one.  
  - **Solution:** Improved scoring/reranking and added more training pairs for tricky cases.  
  - **Impact:** Better ranking of truly relevant sections.

- **Challenge type:** Slow responses  
  - **Challenge itself:** Reranking too many candidate sections was expensive.  
  - **Issue:** Higher latency and poor user experience.  
  - **Solution:** Reduced the number of candidates, cached frequent queries, optimised code.  
  - **Impact:** Faster responses with similar accuracy.

## 4.3 Operational / Practical Challenges
- **Challenge type:** Environment and tooling  
  - **Challenge itself:** Problems with paths, versions, or losing state in notebooks.  
  - **Issue:** Time lost fixing technical issues instead of improving the model.  
  - **Solution:** Standardised folder structure, used config files, wrote setup steps.  
  - **Impact:** Easier to repeat experiments and less time spent on setup.

---

# 5. Summary

- Preprocessing and cleaning made the dataset more reliable and easier to use.  
- The retrieval architecture (embeddings + search + optional reranking) gives a structured way to find relevant sections.  
- Metrics like Hit@k, Precision, Recall, and MRR show how well the system retrieves the right sections and where it still fails.  
- Challenges in data quality, overlapping sections, and tooling were addressed with practical fixes that improved overall performance.
