from sentence_transformers import SentenceTransformer
import psycopg2
import time

DB = {'host': '10.33.16.10', 'port': 5433, 'database': 'dify', 'user': 'yugabyte', 'password': 'yugabyte'}

print("Loading embedding model (first run will download ~90MB)...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print(f"✅ Model loaded! Dimension: {model.get_sentence_embedding_dimension()}")

while True:
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        cur.execute("SELECT id, entity_name, entity_type, description FROM graph_nodes WHERE embedding IS NULL LIMIT 10")
        nodes = cur.fetchall()
        
        if not nodes:
            print("✅ All nodes have embeddings. Sleeping 30s...")
            time.sleep(30)
            continue
        
        for node_id, name, typ, desc in nodes:
            text = f"{name} {typ or ''} {desc or ''}"
            emb = model.encode(text, show_progress_bar=False)
            cur.execute("UPDATE graph_nodes SET embedding = %s WHERE id = %s", (emb.tolist(), node_id))
            print(f"✅ Added embedding: {name}")
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"📊 Batch complete: {len(nodes)} embeddings added\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(10)
