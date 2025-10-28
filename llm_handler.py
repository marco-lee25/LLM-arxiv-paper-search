import os
from typing import List, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import CommaSeparatedListOutputParser, JsonOutputParser
from pydantic.v1 import BaseModel, Field

# --- 1. LLM and Output Parsers Initialization ---

# Initialize the LLM. We'll use GPT-3.5 Turbo for its speed and cost-effectiveness.
# The model will read the OPENAI_API_KEY from your environment variables.
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# Define the desired output structure for query expansion
list_parser = CommaSeparatedListOutputParser()

# Define the desired Pydantic output structure for re-ranking
class PaperRanking(BaseModel):
    relevance_score: int = Field(description="A score from 1 to 10 indicating the paper's relevance to the user's query.")
    justification: str = Field(description="A brief, one-sentence justification for the assigned score.")
    
# Create a JSON output parser from the Pydantic model
json_parser = JsonOutputParser(pydantic_object=PaperRanking)

# --- 2. Query Expansion Function ---

def expand_query_with_llm(query: str) -> List[str]:
    """
    Uses an LLM to expand a user's query into a list of related search terms.

    Args:
        query (str): The user's original search query.

    Returns:
        List[str]: A list of related search terms, including the original query.
    """
    try:
        expansion_prompt_template = """
        You are an expert research assistant in computer science. A user has provided the following query: "{query}".
        Your task is to generate a list of 5-7 related technical keywords, alternative phrasings, or underlying concepts
        that would be useful for searching academic databases like arXiv.
        
        For example, if the query is "inference time timbre-transfer", you might suggest:
        "real-time voice conversion", "audio style transfer", "SDEdit for audio generation", "GAN inversion audio", "voice cloning".

        {format_instructions}
        """
        
        prompt = PromptTemplate(
            template=expansion_prompt_template,
            input_variables=["query"],
            partial_variables={"format_instructions": list_parser.get_format_instructions()}
        )
        
        chain = prompt | llm | list_parser
        
        expanded_terms = chain.invoke({"query": query})
        
        # Ensure the original query is always included
        if query not in expanded_terms:
            expanded_terms.insert(0, query)
            
        return expanded_terms

    except Exception as e:
        print(f"An error occurred during query expansion: {e}")
        # Fallback to just using the original query
        return [query]

# --- 3. Re-ranking Function ---

def rerank_papers_with_llm(papers: List[Dict], query: str) -> List[Dict]:
    """
    Uses an LLM to score and re-rank a list of papers based on a user's query.

    Args:
        papers (List[Dict]): A list of paper dictionaries from search_arxiv.
        query (str): The user's original search query.

    Returns:
        List[Dict]: The list of papers, with added 'relevance_score' and 'justification' fields,
                    sorted by relevance score in descending order.
    """
    reranked_papers = []
    
    rerank_prompt_template = """
    You are an expert research assistant. A user is searching for papers related to: "{query}".
    
    Please evaluate the following academic paper based on its title and abstract. Your task is to determine how relevant it is to the user's query.
    
    Title: {paper_title}
    Abstract: {paper_abstract}
    
    Provide a relevance score from 1 (not relevant at all) to 10 (highly relevant).
    Also, provide a brief, one-sentence justification for your score.

    {format_instructions}
    """
    
    prompt = PromptTemplate(
        template=rerank_prompt_template,
        input_variables=["query", "paper_title", "paper_abstract"],
        partial_variables={"format_instructions": json_parser.get_format_instructions()}
    )
    
    chain = prompt | llm | json_parser
    
    for paper in papers:
        try:
            ranking = chain.invoke({
                "query": query,
                "paper_title": paper["title"],
                "paper_abstract": paper["summary"]
            })
            
            # Add the LLM's ranking to the paper dictionary
            paper.update(ranking)
            reranked_papers.append(paper)
            
        except Exception as e:
            print(f"Could not rank paper '{paper['title']}': {e}")
            # Optionally, assign a default low score if ranking fails
            paper.update({"relevance_score": 0, "justification": "Failed to analyze."})
            reranked_papers.append(paper)
            
    # Sort papers by the new relevance score, descending
    return sorted(reranked_papers, key=lambda x: x["relevance_score"], reverse=True)


if __name__ == '__main__':
    # --- Example Usage ---
    
    # You must have OPENAI_API_KEY set in your environment variables for this to work.
    
    # 1. Test Query Expansion
    test_query = "Using LLMs for code generation"
    print(f"Original Query: '{test_query}'")
    expanded = expand_query_with_llm(test_query)
    print("LLM Expanded Terms:", expanded)
    print("-" * 30)
    
    # 2. Test Re-ranking
    # Let's create some dummy paper data to test the re-ranking logic.
    dummy_papers = [
        {
            "title": "CodeGen: An Open Large Language Model for Code with Multi-Turn Program Synthesis",
            "summary": "We introduce CodeGen, a family of large language models for program synthesis. We find that our models are competitive with state-of-the-art models on a variety of benchmarks.",
            "authors": ["Erik Nijkamp", "Bo Pang"], "pdf_url": "http://example.com/codegen"
        },
        {
            "title": "A Convolutional Neural Network for Modelling Sentences",
            "summary": "We explore the use of Convolutional Neural Networks (CNNs) for sentence-level classification tasks. Our models show strong performance on sentiment analysis and question classification.",
            "authors": ["Nal Kalchbrenner", "Edward Grefenstette"], "pdf_url": "http://example.com/cnn"
        },
        {
            "title": "AlphaCode: Generation of Competitive Programming Code with Large Language Models",
            "summary": "We introduce AlphaCode, a system for code generation that can create novel solutions to competitive programming problems. AlphaCode achieved an estimated rank within the top 54% of human participants.",
            "authors": ["Yujia Li", "David Choi"], "pdf_url": "http://example.com/alphacode"
        }
    ]
    
    print(f"Re-ranking {len(dummy_papers)} papers for query: '{test_query}'")
    reranked = rerank_papers_with_llm(dummy_papers, test_query)
    
    print("\n--- Re-ranked Results ---")
    for paper in reranked:
        print(f"Score: {paper['relevance_score']}/10 - Title: {paper['title']}")
        print(f"Justification: {paper['justification']}")
        print("-" * 20)
