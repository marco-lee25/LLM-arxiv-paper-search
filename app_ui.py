import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
from online_search import search_arxiv
from llm_handler import expand_query_with_llm, rerank_papers_with_llm

class SearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LLM-Powered arXiv Search")
        self.root.geometry("900x700")

        # --- UI Widgets ---
        self.keyword_vars = []
        self.create_widgets()

        # --- Threading and Queue for non-blocking search ---
        self.ui_queue = queue.Queue()
        
    def create_widgets(self):
        # --- Main Frames ---
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        keywords_frame = ttk.LabelFrame(self.root, text="🔍 Expanded Search Terms", padding="10")
        keywords_frame.pack(fill=tk.X, padx=10, pady=5)
        self.keywords_inner_frame = ttk.Frame(keywords_frame)
        self.keywords_inner_frame.pack(fill=tk.X)

        results_frame = ttk.Frame(self.root, padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)

        # --- Top Frame Widgets (Query and Controls) ---
        top_frame.columnconfigure(1, weight=1)

        ttk.Label(top_frame, text="Search Query:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.query_entry = ttk.Entry(top_frame)
        self.query_entry.grid(row=0, column=1, sticky="ew")
        self.query_entry.bind("<Return>", self.start_expansion)

        self.expand_button = ttk.Button(top_frame, text="Expand Query", command=self.start_expansion)
        self.expand_button.grid(row=0, column=2, padx=5)
        
        self.search_button = ttk.Button(top_frame, text="Search with Selected", command=self.start_search, state="disabled")
        self.search_button.grid(row=0, column=3, padx=5)

        ttk.Label(top_frame, text="Top N Results:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.top_n_var = tk.IntVar(value=5)
        top_n_spinbox = ttk.Spinbox(top_frame, from_=1, to=20, textvariable=self.top_n_var, width=5)
        top_n_spinbox.grid(row=1, column=1, sticky="w", pady=(10, 0))

        # --- Results Text Area ---
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, font=("Segoe UI", 10))
        self.results_text.pack(fill=tk.BOTH, expand=True)
        self.results_text.config(state='disabled')

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, padding="5")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def start_expansion(self, event=None):
        query = self.query_entry.get().strip()
        if not query:
            return
        
        self.expand_button.config(state="disabled")
        self.search_button.config(state="disabled")
        self.status_var.set("🧠 Expanding query with LLM...")

        for widget in self.keywords_inner_frame.winfo_children():
            widget.destroy()
        self.keyword_vars.clear()
        
        threading.Thread(target=self.run_expansion_thread, args=(query,), daemon=True).start()
        self.root.after(100, self.check_queue)

    def run_expansion_thread(self, query):
        try:
            expanded_terms = expand_query_with_llm(query)
            self.ui_queue.put({"type": "keywords", "data": expanded_terms})
        except Exception as e:
            self.ui_queue.put({"type": "error", "data": f"Failed to expand query: {e}"})

    def start_search(self, event=None):
        selected_keywords = [var.get() for var in self.keyword_vars if var.get()]
        if not selected_keywords:
            self.update_status("⚠️ Please select at least one search term.")
            return

        query = self.query_entry.get().strip()
        top_n = self.top_n_var.get()
        
        self.search_button.config(state='disabled')
        self.expand_button.config(state='disabled')
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.config(state='disabled')
        
        threading.Thread(target=self.run_search_thread, args=(query, selected_keywords, top_n), daemon=True).start()
        self.root.after(100, self.check_queue)

    def run_search_thread(self, query, search_terms, top_n):
        try:
            self.update_status_in_thread(f"📚 Gathering papers for {len(search_terms)} terms...")
            candidate_papers = []
            seen_titles = set()
            for i, term in enumerate(search_terms):
                self.update_status_in_thread(f"📚 Searching for '{term}' ({i+1}/{len(search_terms)})...")
                papers = search_arxiv(term, max_results=5) # Fetch 5 per term to build a good candidate pool
                for paper in papers:
                    if paper['title'] not in seen_titles:
                        candidate_papers.append(paper)
                        seen_titles.add(paper['title'])
            
            if not candidate_papers:
                self.ui_queue.put({"type": "error", "data": "No papers found. Please try a different query."})
                return

            self.update_status_in_thread(f"🔍 Re-ranking {len(candidate_papers)} papers with LLM...")
            reranked_papers = rerank_papers_with_llm(candidate_papers, query)
            
            self.ui_queue.put({"type": "results", "data": (reranked_papers, top_n)})

        except Exception as e:
            self.ui_queue.put({"type": "error", "data": f"An unexpected error occurred: {e}"})

    def update_status_in_thread(self, message):
        self.ui_queue.put({"type": "status", "data": message})

    def check_queue(self):
        try:
            message = self.ui_queue.get_nowait()
            msg_type = message.get("type")
            msg_data = message.get("data")

            if msg_type == "status":
                self.status_var.set(msg_data)
            elif msg_type == "keywords":
                self.display_keywords(msg_data)
                self.status_var.set("✅ Expansion complete. Select terms and click Search.")
                self.expand_button.config(state='normal')
                self.search_button.config(state='normal')
                return 
            elif msg_type == "results":
                reranked_papers, top_n = msg_data
                self.display_results(reranked_papers, top_n)
                self.status_var.set("✅ Done!")
                self.expand_button.config(state='normal')
                self.search_button.config(state='normal')
                return
            elif msg_type == "error":
                self.display_error(msg_data)
                self.status_var.set("❌ Error!")
                self.expand_button.config(state='normal')
                self.search_button.config(state='normal')
                return

        except queue.Empty:
            pass
        
        self.root.after(100, self.check_queue)

    def display_keywords(self, keywords):
        for keyword in keywords:
            var = tk.StringVar(value=keyword)
            cb = ttk.Checkbutton(self.keywords_inner_frame, text=keyword, variable=var, onvalue=keyword, offvalue="")
            cb.pack(anchor="w", padx=5, pady=2)
            self.keyword_vars.append(var)

    def display_results(self, papers, top_n):
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        
        for i, paper in enumerate(papers[:top_n], 1):
            self.results_text.insert(tk.END, f"--- RANK {i} ---\n", ('h1',))
            self.results_text.insert(tk.END, f"📄 Title: {paper['title']}\n", ('h2',))
            self.results_text.insert(tk.END, f"👥 Authors: {', '.join(paper['authors'])}\n")
            self.results_text.insert(tk.END, f"🔗 PDF Link: {paper['pdf_url']}\n")
            self.results_text.insert(tk.END, f"⭐ LLM Score: {paper.get('relevance_score', 'N/A')}/10\n", ('bold',))
            self.results_text.insert(tk.END, f"💬 Justification: {paper.get('justification', 'N/A')}\n\n")

        self.results_text.tag_config('h1', font=('Segoe UI', 14, 'bold'))
        self.results_text.tag_config('h2', font=('Segoe UI', 11, 'bold'))
        self.results_text.tag_config('bold', font=('Segoe UI', 10, 'bold'))
        self.results_text.config(state='disabled')
        
    def display_error(self, error_message):
        self.results_text.config(state='normal')
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"An error occurred:\n\n{error_message}", ('error',))
        self.results_text.tag_config('error', font=('Segoe UI', 10, 'bold'), foreground='red')
        self.results_text.config(state='disabled')

if __name__ == '__main__':
    root = tk.Tk()
    app = SearchApp(root)
    root.mainloop()
