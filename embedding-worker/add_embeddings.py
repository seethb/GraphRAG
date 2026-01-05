#!/usr/bin/env python3
import psycopg2
from sentence_transformers import SentenceTransformer
import time

DB = {
    'host': '10.33.16.10',
    'port': 5433,
    'database': 'dify',
    'user': 'yugabyte',
    'password': 'yugabyte'
}

print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print(f"Model loaded! Dimension: {model.get_sentence_embedding_dimension()}")

def add_embeddings_batch():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, entity_name, entity_type, description
        FROM graph_nodes
        WHERE embedding IS NULL
        LIMIT 10
    """)
    
    nodes = cur.fetchall()
    
    if not nodes:
        return 0
    
    embeddings_added = 0
    for node_id, name, typ, desc in nodes:
        text = f"{name} {typ or ''} {desc or ''}"
        embedding = model.encode(text, show_progress_bar=False)
        
        cur.execute("""
            UPDATE graph_nodes
            SET embedding = %s
            WHERE id = %s
        """, (embedding.tolist(), node_id))
        embeddings_added += 1
        print(f"Added embedding for: {name}")
    
    conn.commit()
    cur.close()
    conn.close()
    
    return embeddings_added

if __name__ == '__main__':
    print("Starting embedding worker...")
    
    while True:
        try:
            added = add_embeddings_batch()
            if added > 0:
                print(f"✅ Added {added} embeddings")
            else:
                print("All nodes have embeddings. Sleeping...")
                time.sleep(30)
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)
