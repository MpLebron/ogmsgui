import requests
import tenacity
from openai import OpenAI

class AcademicQueryService:
    def __init__(self, api_key: str = "sk-rb7CtWXJ6AXWCiavF80eA074B3704438B7C855C3D623Bb25", 
                 modelingContext: str = "",
                 base_url: str = "https://aihubmix.com/v1"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.modelingContext = modelingContext
    
    async def get_academic_question_answer(self, query: str) -> dict:
        """
        获取学术问题的答案（这是对外暴露的主要接口）
        """
        paper_list = await self._get_academic_question_answer_list(query)
        question_answer = await self._get_openai_summary(query, paper_list)
        return {
            "question": query, 
            "answer": question_answer, 
            "paperList": paper_list
        }

    @tenacity.retry(wait=tenacity.wait_fixed(1), stop=tenacity.stop_after_attempt(5))
    async def _get_academic_question_answer_list(self, query: str, page: int = 1, size: int = 10) -> list:
        """内部方法：获取论文列表"""
        url = "https://consensus.app/api/paper_search/?query=" + query + "&page=" + str(page) + "&size=" + str(size)
        payload={}
        headers = {
            'Referer': 'https://consensus.app',
            'User-Agent': 'Apifox/1.0.0 (https://apifox.com)'
        }
        response = requests.request("GET", url, headers=headers, data=payload).json()
        
        # return top 10 result in claims
        top10Claims = response["papers"][:10]
        return top10Claims

    async def _get_openai_summary(self, query: str, paper_list: list) -> str:
        """内部方法：获取 OpenAI 总结"""
        paperContext = ""
        for paper in paper_list:
            # 组织成，这是一篇名为<title>的论文，发表在<journal>上，相关的内容为<display_text>。
            paperContext += "This is a paper named: " + paper["title"] + " published in: " + paper["journal"] + ". The related content is: " + paper["display_text"] + "."
        
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI researcher assistant. User is now conducting scientific geoscience research. The modeling history is: " + self.modelingContext + ". He/she is now asking a question about " + query + ".  And here are some information related to this question: " + paperContext + ". And your task is to summarize the information and answer the question."},
                {
                    "role": "user",
                    "content": "Besides your summary, you should not reply any other information. Below is your answer to the question based on the information provided: " 
                }
            ]
        )
        return completion.choices[0].message.content