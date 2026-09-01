import chromadb
import logging
from chromadb.config import Settings
from chromadb.errors import NotFoundError

logger = logging.getLogger("vector-store")


class VectorStore:
    def __init__(self, persist_dir: str = "./data/chroma_db"):
        """
        初始化向量数据库客户端，使用磁盘持久化模式
        :param persist_dir: 向量数据存储路径
        """
        try:
            logger.info(f"[向量库初始化] 开始连接，持久化路径：{persist_dir}")
            # 配置持久化目录，重启服务数据不丢失
            self.client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            logger.info("[向量库初始化] 连接成功")
        except Exception as e:
            logger.error(f"[向量库初始化] 连接失败：{str(e)}", exc_info=True)
            raise RuntimeError("向量数据库连接失败，请检查服务配置") from e

    def get_or_create_collection(self, collection_name: str = "documents"):
        """
        获取或创建集合（类似关系型数据库的表）
        :param collection_name: 集合名称
        :return: 集合对象
        """
        collection = self.client.get_or_create_collection(
            name=collection_name,
            # 使用默认内置embedding，明天替换DeepSeek Embedding
            metadata={"description": "文档知识库向量集合"}
        )
        return collection

    def search_similar(self, query_vector: list[float | int], top_n: int = 3, filter=None) -> list[dict]:
        """
        根据查询向量，检索最相似的文档片段
        :param query_vector: 问题的向量化结果
        :param top_n: 返回最相关的条数
        :return: 列表，每个元素包含文本内容、元数据、相似度分数
        """
        try:
            logger.info(f"[向量库检索] 开始相似度检索，top_n={top_n}")
            collection = self.get_or_create_collection()

            # 调用ChromaDB相似度查询
            results = collection.query(
                query_embeddings=[query_vector],
                n_results=top_n,
                include=["documents", "metadatas", "distances"],
                where=filter
            )

            logger.info(
                f"[调试] 返回分块元数据样本：{results['metadatas'][0][0] if results['metadatas'] and results['metadatas'][0] else '无数据'}")

            # 整理返回格式，方便上层使用
            result_list = []
            for doc, meta, distance in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
                result_list.append({"content": doc, "metadata": meta, "distance": distance})

            logger.info(f"[向量库检索] 检索完成，命中 {len(result_list)} 条相关文档")
            return result_list
        except Exception as e:
            logger.error(f"[向量库检索] 检索失败：{str(e)}", exc_info=True)
            raise RuntimeError("向量库检索失败，请稍后重试") from e

    def add_documents(self, collection_name: str, ids: list, documents: list, metadatas: list = None):
        """
        批量添加文档到向量库
        :param collection_name: 集合名称
        :param ids: 文档唯一ID列表
        :param documents: 文本内容列表
        :param metadatas:元数据列表，用于存储文档来源，页码等附属信息
        """
        try:
            logger.info(f"[向量库入库] 开始添加文档，集合：{collection_name}，文档数量：{len(documents)}")
            collection = self.get_or_create_collection(collection_name)
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            logger.info(f"[向量库入库] 添加文档成功，集合：{collection_name}，文档数量：{len(documents)}")
        except Exception as e:
            logger.error(f"[向量库入库] 添加文档失败：{str(e)}", exc_info=True)
            raise RuntimeError("向量库存储失败，请稍后重试") from e

    def add_documents_with_embeddings(
            self,
            collection_name: str,
            ids: list[str],
            documents: list[str],
            embeddings: list[list[float | int]],
            metadatas: list[dict] = None
    ):
        """
        批量插入带自定义向量的文档到向量库
        :param collection_name: 集合名称
        :param ids: 文档 ID 列表，顺序与文档一一对应
        :param documents: 文档文本内容列表
        :param embeddings: 预生成的向量列表，顺序与文档对应
        :param metadatas: 元数据列表，可选
        """
        try:
            logger.info(f"[向量库入库] 开始添加带向量文档，集合：{collection_name}，文档块数量：{len(documents)}")
            collection = self.get_or_create_collection(collection_name)
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas if metadatas else [{} for _ in ids]
            )
            logger.info(f"[向量库入库] 带向量文档添加成功，集合：{collection_name}，文档块数量：{len(documents)}")
        except Exception as e:
            logger.error(f"[向量库入库] 带向量文档添加失败：{str(e)}", exc_info=True)
            raise RuntimeError("向量存储失败，请稍后重试") from e

    def query_documents(self, collection_name: str, query_text: str, top_k: int = 3):
        """
        以相似度搜索：根据查询文本，返回最相关的Top K条文档
        :param collection_name: 集合名称
        :param query_text: 查询文本
        :param top_k: 返回最相关的条数
        :return: 搜索结果字典，包含文档、距离、元数据
        """
        try:
            logger.info(f"[向量库检索] 开始文本检索，集合：{collection_name}，top_k={top_k}")
            collection = self.get_or_create_collection(collection_name)
            results = collection.query(
                query_texts=[query_text],
                n_results=top_k
            )
            doc_count = len(results.get("documents", [[]])[0])
            logger.info(f"[向量库检索] 文本检索完成，集合：{collection_name}，命中文档数量：{doc_count}")
            return results
        except Exception as e:
            logger.error(f"[向量库检索] 文本检索失败：{str(e)}", exc_info=True)
            raise RuntimeError("向量检索失败，请稍后重试") from e

    def query_by_embedding(
            self,
            collection_name: str,
            query_embedding: list[float | int],
            top_k: int = 3
    ) -> list:
        """
        使用自定义向量进行相似度检索
        :param collection_name: 集合名称
        :param query_embedding: 查询文本的预生成向量
        :param top_k: 返回最相似的结果数量
        :return: 检索结果列表，包含文本、元数据、相似度
        """
        try:
            logger.info(f"[向量库检索] 开始向量检索，集合：{collection_name}，top_k={top_k}")
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

            logger.info(f"[向量库检索] 向量检索完成，集合：{collection_name}，命中文档数量：{len(result_list)}")
            return result_list
        except Exception as e:
            logger.error(f"[向量库检索] 向量检索失败：{str(e)}", exc_info=True)
            raise RuntimeError("向量检索失败，请稍后重试") from e

    def delete_collection(self, collection_name: str):
        """删除指定集合，用于调试清空数据"""
        try:
            logger.info(f"[向量库删除] 开始删除集合：{collection_name}")
            self.client.delete_collection(collection_name)
            logger.info(f"[向量库删除] 集合删除成功：{collection_name}")
        except NotFoundError:
            # 集合不存在时忽略错误
            logger.warning(f"[向量库删除] 集合不存在，跳过：{collection_name}")
            pass
        except Exception as e:
            logger.error(f"[向量库删除] 集合删除失败：{str(e)}", exc_info=True)
            raise RuntimeError("向量库集合删除失败") from e


# 全局单例，供业务层直接调用
vector_store = VectorStore()
