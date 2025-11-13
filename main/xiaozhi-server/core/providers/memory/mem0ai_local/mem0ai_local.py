import traceback
import requests

from ..base import MemoryProviderBase, logger
from mem0 import MemoryClient
from core.utils.util import check_model_key

TAG = __name__


class MemoryProvider(MemoryProviderBase):
    def __init__(self, config, summary_memory=None):
        super().__init__(config)
        self.api_host = config.get("api_host", "")
        self.use_mem0 = True

        if not self.api_host:
            logger.bind(tag=TAG).error("api_host 未配置，无法使用记忆服务")
            self.use_mem0 = False
        else:
            logger.bind(tag=TAG).info(f"成功配置 Memory REST 接口: {self.api_host}")

    async def save_memory(self, msgs):
        if not self.use_mem0:
            return None
        if len(msgs) < 2:
            return None

        try:
            # Format the content as a message list for mem0
            messages = [
                {"role": message.role, "content": message.content}
                for message in msgs
                if message.role != "system"
            ]
            url = f"{self.api_host}/memories"
            payload = {
                "messages": messages,
                "user_id": self.role_id,
                "agent_id": "",
                "run_id": "",
                "metadata": {}
            }

            headers = {"Content-Type": "application/json", "accept": "application/json"}
            response = requests.post(url, json=payload, headers=headers)

            result = response.json()
            logger.bind(tag=TAG).debug(f"Save memory result: {result}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"保存记忆失败: {str(e)}")
            return None

    async def query_memory(self, query: str) -> str:
        if not self.use_mem0:
            return ""
        try:
            url = f"{self.api_host}/search"
            payload = {
                "query": query,
                "user_id": self.role_id,
                "run_id": "",
                "agent_id": "",
                "filters": {}
            }

            headers = {"Content-Type": "application/json", "accept": "application/json"}
            response = requests.post(url, json=payload, headers=headers)
            results = response.json()
            if not results or "results" not in results:
                return ""

            # Format each memory entry with its update time up to minutes
            memories = []
            for entry in results["results"]:
                # timestamp = entry.get("updated_at", "")
                timestamp = entry.get("created_at", "")
                if timestamp:
                    try:
                        # Parse and reformat the timestamp
                        dt = timestamp.split(".")[0]  # Remove milliseconds
                        formatted_time = dt.replace("T", " ")
                    except:
                        formatted_time = timestamp
                memory = entry.get("memory", "")
                if timestamp and memory:
                    # Store tuple of (timestamp, formatted_string) for sorting
                    memories.append((timestamp, f"[{formatted_time}] {memory}"))

            # Sort by timestamp in descending order (newest first)
            memories.sort(key=lambda x: x[0], reverse=True)

            # Extract only the formatted strings
            memories_str = "\n".join(f"- {memory[1]}" for memory in memories)
            logger.bind(tag=TAG).debug(f"Query results: {memories_str}")
            return memories_str
        except Exception as e:
            logger.bind(tag=TAG).error(f"查询记忆失败: {str(e)}")
            return ""
