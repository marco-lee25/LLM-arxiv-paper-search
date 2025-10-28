import argparse
from online_search import search_arxiv
from llm_handler import expand_query_with_llm, rerank_papers_with_llm

def main():
    # --- 1. Setup Command-Line Argument Parser ---
    parser = argparse.ArgumentParser(description="An LLM-powered academic paper search engine for arXiv.")
    parser.add_argument("query", type=str, help="The search query for academic papers.")
    parser.add_argument("--max_results_per_term", type=int, default=5, help="Maximum number of papers to fetch for each search term.")
    parser.add_argument("--top_n", type=int, default=5, help="Number of final ranked papers to display.")
    
    args = parser.parse_args()
    
    initial_query = args.query
    max_results = args.max_results_per_term
    top_n = args.top_n
    
    print(f"🚀 Starting search for: '{initial_query}'")
    
    # --- 2. Expand Query with LLM ---
    print("\n🧠 Step 1: Expanding query with LLM for broader search...")
    search_terms = expand_query_with_llm(initial_query)
    print(f"   Expanded search terms: {search_terms}")
    
    # --- 3. Gather Candidate Papers from arXiv ---
    print(f"\n📚 Step 2: Gathering candidate papers from arXiv (fetching up to {max_results} for each term)...")
    candidate_papers = []
    seen_titles = set()
    
    for term in search_terms:
        print(f"   Searching for: '{term}'")
        papers = search_arxiv(term, max_results=max_results)
        for paper in papers:
            if paper['title'] not in seen_titles:
                candidate_papers.append(paper)
                seen_titles.add(paper['title'])
    
    if not candidate_papers:
        print("\n❌ No papers found after searching with all terms. Please try a different query.")
        return
        
    print(f"   Found a total of {len(candidate_papers)} unique candidate papers.")
    
    # --- 4. Re-rank Papers with LLM ---
    print("\n🔍 Step 3: Re-ranking papers with LLM for relevance...")
    reranked_papers = rerank_papers_with_llm(candidate_papers, initial_query)
    
    # --- 5. Display Final Results ---
    print(f"\n🏆 Top {top_n} Most Relevant Papers for '{initial_query}':")
    print("=" * 50)
    
    for i, paper in enumerate(reranked_papers[:top_n], 1):
        print(f"--- RANK {i} ---")
        print(f"📄 Title: {paper['title']}")
        print(f"👥 Authors: {', '.join(paper['authors'])}")
        print(f"🔗 PDF Link: {paper['pdf_url']}")
        print(f"⭐ LLM Score: {paper.get('relevance_score', 'N/A')}/10")
        print(f"💬 Justification: {paper.get('justification', 'N/A')}")
        print("-" * 20)

if __name__ == '__main__':
    # Make sure you have your OPENAI_API_KEY set as an environment variable
    # before running this script.
    main()
