import arxiv
from typing import List, Dict

def search_arxiv(query: str, max_results: int = 10) -> List[Dict]:
    """
    Searches the arXiv API for a given query and returns a list of papers.

    Args:
        query (str): The search query.
        max_results (int): The maximum number of results to return.

    Returns:
        List[Dict]: A list of dictionaries, where each dictionary represents a paper
                    and contains its title, authors, summary (abstract), and pdf_url.
    """
    try:
        # Search for papers
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance
        )

        results = []
        for result in search.results():
            paper = {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "summary": result.summary,
                "pdf_url": result.pdf_url
            }
            results.append(paper)
        
        return results

    except Exception as e:
        print(f"An error occurred while searching arXiv: {e}")
        return []

if __name__ == '__main__':
    # Example usage:
    test_query = "DDIM inversion for image editing"
    print(f"Searching for: '{test_query}'")
    papers = search_arxiv(test_query, max_results=5)

    if papers:
        print(f"Found {len(papers)} papers:")
        for i, paper in enumerate(papers, 1):
            print(f"--- Paper {i} ---")
            print(f"Title: {paper['title']}")
            print(f"Authors: {', '.join(paper['authors'])}")
            print(f"Abstract: {paper['summary'][:200]}...") # Print first 200 chars of abstract
            print(f"PDF Link: {paper['pdf_url']}")
            print("-" * 20)
    else:
        print("No papers found or an error occurred.")
