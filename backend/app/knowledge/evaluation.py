import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal
from backend.app.models.knowledge import AitEntity
from backend.app.models.automation import KnowledgeEvaluation

# Golden Evaluation Test Dataset covering all 16 required academic and campus domains
GOLDEN_EVALUATION_QUERIES = [
    {
        "domain": "BCA",
        "query": "What is the duration and curriculum for BCA at AIT?",
        "expected_keywords": ["bca", "3 years", "computer applications", "semester"],
    },
    {
        "domain": "BBA",
        "query": "Does AIT offer BBA and what are the major specializations?",
        "expected_keywords": ["bba", "management", "business", "administration"],
    },
    {
        "domain": "MCA",
        "query": "Tell me about MCA eligibility at AIT.",
        "expected_keywords": ["mca", "postgraduate", "eligibility", "computer"],
    },
    {
        "domain": "MBA",
        "query": "What MBA specializations are offered at Ahmedabad Institute of Technology?",
        "expected_keywords": ["mba", "marketing", "finance", "hr", "management"],
    },
    {
        "domain": "B.Tech CSE",
        "query": "What is the intake and focus of B.Tech Computer Science and Engineering?",
        "expected_keywords": ["computer science", "engineering", "cse", "coding", "software"],
    },
    {
        "domain": "B.Tech IT",
        "query": "What is covered under B.Tech Information Technology?",
        "expected_keywords": ["information technology", "networking", "database", "it"],
    },
    {
        "domain": "Faculty",
        "query": "Who is the principal or head of departments at AIT?",
        "expected_keywords": ["principal", "hod", "professor", "faculty"],
    },
    {
        "domain": "Subjects",
        "query": "What subjects are taught in engineering first year at AIT?",
        "expected_keywords": ["mathematics", "physics", "programming", "engineering"],
    },
    {
        "domain": "Fees",
        "query": "What is the fee structure for courses at AIT?",
        "expected_keywords": ["fee", "tuition", "frt", "semester", "rupees"],
    },
    {
        "domain": "Admissions",
        "query": "How can I apply for admission to AIT Ahmedabad?",
        "expected_keywords": ["acpc", "admission", "merit", "eligibility", "quota"],
    },
    {
        "domain": "Facilities",
        "query": "What campus facilities exist at AIT?",
        "expected_keywords": ["canteen", "auditorium", "wifi", "sports", "campus"],
    },
    {
        "domain": "Library",
        "query": "Tell me about the central library at AIT.",
        "expected_keywords": ["library", "books", "journals", "reading", "digital"],
    },
    {
        "domain": "Labs",
        "query": "Are there specialized computer and hardware labs at AIT?",
        "expected_keywords": ["lab", "computer", "electronics", "high-speed", "practical"],
    },
    {
        "domain": "Events",
        "query": "What technical and cultural events happen at AIT?",
        "expected_keywords": ["techfest", "cultural", "hackathon", "annual", "event"],
    },
    {
        "domain": "Placement",
        "query": "How is the placement record and top recruiters at AIT?",
        "expected_keywords": ["placement", "recruiter", "tcs", "package", "training"],
    },
    {
        "domain": "Academic Information",
        "query": "Which university is AIT affiliated with and what is the exam pattern?",
        "expected_keywords": ["gtu", "gujarat technological university", "affiliated", "exam"],
    }
]

def run_golden_evaluation_suite() -> Dict[str, Any]:
    """
    Executes the golden evaluation suite across all 16 domains against the active verified AIT knowledge store.
    Records evaluation metrics and detects regression.
    """
    db: Session = SessionLocal()
    try:
        entities = db.query(AitEntity).filter(AitEntity.is_verified == True).all()
        aggregated_parts = []
        for e in entities:
            aggregated_parts.append(f"{e.name} {e.category} {e.code or ''}")
            if isinstance(e.details, dict):
                for k, v in e.details.items():
                    aggregated_parts.append(f"{k} {v}")
            elif isinstance(e.details, str):
                aggregated_parts.append(e.details)
        aggregated_knowledge = " ".join(aggregated_parts).lower()


        domain_scores = {}
        total_queries = len(GOLDEN_EVALUATION_QUERIES)
        passed_queries = 0
        detailed_results = []

        for item in GOLDEN_EVALUATION_QUERIES:
            domain = item["domain"]
            keywords = item["expected_keywords"]
            
            # Check how many expected keywords match the verified knowledge
            matched = [k for k in keywords if k in aggregated_knowledge]
            match_ratio = len(matched) / max(len(keywords), 1)
            passed = match_ratio >= 0.5

            if passed:
                passed_queries += 1

            score = round(match_ratio * 100, 1)
            domain_scores[domain] = score
            detailed_results.append({
                "domain": domain,
                "query": item["query"],
                "passed": passed,
                "score": score,
                "matched_keywords": matched
            })

        accuracy = round((passed_queries / total_queries) * 100, 1)

        # Check for regression against last evaluation
        previous_eval = db.query(KnowledgeEvaluation).order_by(KnowledgeEvaluation.created_at.desc()).first()
        regression_detected = False
        if previous_eval and accuracy < (previous_eval.accuracy_score - 2.0):
            regression_detected = True

        version_tag = f"v{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
        record = KnowledgeEvaluation(
            version_tag=version_tag,
            total_queries=total_queries,
            passed_queries=passed_queries,
            failed_queries=total_queries - passed_queries,
            accuracy_score=accuracy,
            regression_detected=regression_detected,
            domain_scores=domain_scores,
            detailed_results=detailed_results,
            evaluated_by="AutomatedEvaluationWorker"
        )
        db.add(record)
        db.commit()

        return {
            "status": "SUCCESS",
            "version_tag": version_tag,
            "accuracy_score": accuracy,
            "passed_queries": passed_queries,
            "total_queries": total_queries,
            "regression_detected": regression_detected,
            "can_publish": not regression_detected,
            "domain_scores": domain_scores
        }
    finally:
        db.close()
