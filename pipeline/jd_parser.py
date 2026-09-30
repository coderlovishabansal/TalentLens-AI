"""
Parses the Job Description into structured requirements used by the scoring pipeline.
Hardcoded for the Redrob Senior AI Engineer JD — change this for a different JD.
"""

JD_RAW = """
Senior AI Engineer — Founding Team at Redrob AI.
Location: Pune/Noida, India. Hybrid. Open to Hyderabad, Mumbai, Delhi NCR.
Experience: 5-9 years. 4-5 years in applied ML/AI at product companies.

Must have:
- Production embeddings-based retrieval systems (sentence-transformers, BGE, E5, OpenAI embeddings)
- Vector databases or hybrid search (Pinecone, Weaviate, Qdrant, Milvus, Elasticsearch, FAISS)
- Strong Python, code quality
- Ranking evaluation frameworks: NDCG, MRR, MAP, A/B testing, offline-to-online correlation
- Shipped end-to-end ranking, search, or recommendation system to real users at scale

Nice to have:
- LLM fine-tuning (LoRA, QLoRA, PEFT)
- Learning to rank (XGBoost, neural LTR)
- HR-tech, recruiting tech, marketplace products
- Distributed systems, large-scale inference optimization
- Open source contributions in AI/ML

Hard disqualifiers:
- Pure research background with no production deployment
- AI experience is only recent LangChain/OpenAI wrappers (under 12 months), no prior ML production
- Has not written production code in last 18 months (pure architecture/tech lead role)
- Entire career at consulting firms: TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini
- Primary expertise is computer vision, speech, or robotics with no NLP/IR experience

Preferred traits:
- Plans to stay 3+ years (not a title-chaser switching every 1.5 years)
- Writes well, async-first communication
- Has shipped ranking/search/recommendation at meaningful scale
- Active on job market or Redrob platform
"""

JD_REQUIREMENTS = {
    "raw_text": JD_RAW,

    "must_have_skills": [
        "embeddings", "vector database", "retrieval", "semantic search",
        "ranking", "recommendation", "information retrieval",
        "sentence transformers", "faiss", "elasticsearch", "pinecone",
        "qdrant", "weaviate", "milvus", "opensearch",
        "python", "nlp", "natural language processing",
        "ndcg", "mrr", "a/b testing", "evaluation", "re-ranking",
        "hybrid search", "dense retrieval", "bm25",
    ],

    "nice_to_have_skills": [
        "lora", "qlora", "peft", "fine-tuning", "fine tuning",
        "learning to rank", "xgboost", "lightgbm",
        "distributed systems", "inference optimization",
        "transformers", "bert", "llm", "large language model",
        "open source", "pytorch", "tensorflow",
    ],

    "strong_title_signals": [
        "machine learning engineer", "ml engineer", "ai engineer",
        "search engineer", "ranking engineer", "nlp engineer",
        "data scientist", "applied scientist", "research engineer",
        "senior engineer", "software engineer",
        "recommendation", "retrieval",
    ],

    "weak_title_signals": [
        "marketing", "sales", "hr", "accountant", "graphic designer",
        "civil engineer", "mechanical engineer", "customer support",
        "content writer", "business analyst", "operations manager",
        "project manager",
    ],

    "consulting_companies": [
        "tcs", "tata consultancy", "infosys", "wipro", "accenture",
        "cognizant", "capgemini", "hcl", "tech mahindra", "mphasis",
        "hexaware", "l&t infotech", "ltimindtree",
    ],

    "good_industries": [
        "technology", "software", "internet", "e-commerce", "fintech",
        "saas", "product", "startup", "ai", "data",
    ],

    "experience_min": 5,
    "experience_max": 9,
    "experience_ideal_min": 6,
    "experience_ideal_max": 8,

    "preferred_locations": [
        "pune", "noida", "delhi", "mumbai", "hyderabad", "bangalore",
        "bengaluru", "india",
    ],

    "notice_period_ideal_days": 30,
    "notice_period_max_days": 90,
}


def get_jd_text_for_embedding() -> str:
    """Returns a clean text representation of the JD for embedding."""
    return (
        "Senior AI Engineer role requiring production experience with embeddings-based retrieval, "
        "vector databases, semantic search, hybrid search, ranking systems, recommendation engines, "
        "NLP, information retrieval, Python, NDCG MRR evaluation, A/B testing, "
        "sentence-transformers, FAISS, Elasticsearch, Pinecone, Qdrant, Weaviate, "
        "LLM integration, re-ranking, dense retrieval BM25 hybrid. "
        "5-9 years experience at product companies. "
        "Must have shipped ranking or search or recommendation to real users at scale."
    )


def get_jd() -> dict:
    return JD_REQUIREMENTS
