import chromadb
from chromadb.config import Settings
from chromadb.errors import NotFoundError

class VectorStore:
    def __init__(self, persist_dir: str = "./data/chroma_db"):
        """
        初始化向量数据库客户端，使用磁盘持久化模式
        :param persist_dir: 向量数据存储路径
        """
        # 配置持久化目录，重启服务数据不丢失
        self.client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False)
        )

    def get_or_create_collection(self, collection_name: str = "documents"):
        """
        获取或创建集合（类似关系型数据库的表）
        :param collection_name: 集合名称
        :return: 集合对象
        """
        collection = self.client.get_or_create_collection(
            name=collection_name,
            # 使用默认内置embedding，明天替换DeepSeek Embedding
            metadata={"description":"文档知识库向量集合"}
        )
        return collection

    def search_similar(self,query_vector: list[float], top_n: int = 3) -> list[dict]:
        """
        根据查询向量，检索最相似的文档片段
        :param query_vector: 问题的向量化结果
        :param top_n: 返回最相关的条数
        :return: 列表，每个元素包含文本内容、元数据、相似度分数
        """
        collection = self.get_or_create_collection()

        #  调用ChromaDB相似度查询
        results = collection.query(
            query_embeddings=[query_vector],
            n_results=top_n,
            include=["documents", "metadatas", "distances"]
        )

        # 整理返回格式，方便上层使用
        result_list = []
        for doc, meta, distance in zip(results["documents"][0],results["metadatas"][0],results["distances"][0]):
            result_list.append({"content": doc, "metadata": meta, "distance": distance})

        return result_list


    def add_documents(self, collection_name: str, ids: list, documents: list, metadatas: list = None):
        """
        批量添加文档到向量库
        :param collection_name: 集合名称
        :param ids: 文档唯一ID列表
        :param documents: 文本内容列表
        :param metadatas:元数据列表，用于存储文档来源，页码等附属信息
        """
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def add_documents_with_embeddings(
            self,
            collection_name: str,
            ids: list[str],
            documents: list[str],
            embeddings: list[list[float]],
            metadatas: list[dict] = None
    ):
        """
        批量插入带自定义向量的文档到向量库
        :param collection_name: 集合名称
        :param ids: 文档 ID 列表，顺序与文档一一对应
        :param documents: 文档文本内容列表
        :param embeddings:预生成的向量列表，顺序与文档
        :param metadatas: 元数据列表，可选
        """
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas if metadatas else [{} for _ in ids]
        )

    def query_documents(self, collection_name: str, query_text: str, top_k: int = 3):
        """
        相似度搜索：根据查询文本，返回最相关的Top K条文档
        :param collection_name: 集合名称
        :param query_text: 查询文本
        :param top_k: 返回最相关的条数
        :return: 搜索结果字典，包含文档、距离、元数据
        """
        collection = self.get_or_create_collection(collection_name)
        results = collection.query(
            query_texts=[query_text],
            n_results=top_k
        )
        return results

    def query_by_embedding(
            self,
            collection_name: str,
            query_embedding: list[float],
            top_k: int = 3
    ) -> list:
        """
        使用自定义向量进行相似度检索
        :param collection_name: 集合名称
        :param query_embedding: 查询文本的预生成向量
        :param top_k: 返回最相似的结果数量
        :return: 检索结果列表，包含文本、元数据、相似度
        """
        collection = self.get_or_create_collection(collection_name)
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        # 格式化返回结果
        result_list = []
        for i in range(len(results["ids"][0])):
            result_list.append({
                "id": results["ids"][0][i],
                "text": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
        return result_list

    def delete_collection(self, collection_name: str):
        """删除指定集合，用于调试清空数据"""
        try:
            self.client.delete_collection(collection_name)
        except NotFoundError:
            # 集合不存在时忽略错误
            pass

# 全局单例，供业务层直接调用
vector_store = VectorStore()















