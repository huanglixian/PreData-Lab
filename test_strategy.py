from app.chunk_func.base import BaseChunkStrategy

class TestChunkStrategy(BaseChunkStrategy):
    def get_metadata(self):
        return {
            'name': 'test',
            'display_name': '测试策略',
            'description': '这是一个测试策略',
            'supported_types': ['.txt', '.md']
        }
    
    def chunk_no_meta(self, text, chunk_size=1000, chunk_overlap=200):
        chunks = []
        # 简单按行分割
        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            current_chunk.append(line)
            current_length += len(line) + 1  # +1 for newline
            
            if current_length >= chunk_size:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
            
        return chunks 