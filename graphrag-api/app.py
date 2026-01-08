from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import psycopg2
import json
import os

app = Flask(__name__)
CORS(app)

DB = {
    'host': 'yugabytedb',
    'port': 5433,
    'database': 'graphrag',
    'user': 'yugabyte',
    'password': 'yugabyte'
}

# Initialize sentence transformer for local embeddings
embedder = None
EMBEDDINGS_AVAILABLE = False

def init_embedder():
    """Initialize the embedding model (lazy loading)"""
    global embedder, EMBEDDINGS_AVAILABLE
    if embedder is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("Loading embedding model...")
            # Using a lightweight model (384 dimensions)
            embedder = SentenceTransformer('all-MiniLM-L6-v2')
            EMBEDDINGS_AVAILABLE = True
            print("Embedding model loaded successfully!")
        except Exception as e:
            print(f"Failed to load embedding model: {e}")
            EMBEDDINGS_AVAILABLE = False
    return embedder

def get_embedding(text: str):
    """Generate embedding for text using local model"""
    try:
        model = init_embedder()
        if model is None:
            return None
        
        # Clean text
        text = text.replace("\n", " ").strip()
        if not text:
            return None
        
        # Generate embedding (returns 384-dimensional vector)
        embedding = model.encode(text, show_progress_bar=False)
        return embedding.tolist()
    except Exception as e:
        print(f"Embedding error: {e}")
        return None

@app.route('/health', methods=['GET'])
def health():
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM graph_nodes')
        nodes = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM graph_edges')
        edges = cur.fetchone()[0]
        
        # Check how many nodes have embeddings
        cur.execute('SELECT COUNT(*) FROM graph_nodes WHERE embedding IS NOT NULL')
        nodes_with_embeddings = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'ok', 
            'nodes': nodes, 
            'edges': edges,
            'nodes_with_embeddings': nodes_with_embeddings,
            'embeddings_enabled': EMBEDDINGS_AVAILABLE,
            'embedding_model': 'all-MiniLM-L6-v2 (384d)'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'msg': str(e)}), 500

@app.route('/graph/search', methods=['POST'])
def search():
    try:
        data = request.json
        query = data.get('query', '')
        
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, entity_name, entity_type, description
            FROM graph_nodes
            WHERE entity_name ILIKE %s OR description ILIKE %s
            LIMIT 3
        """, (f'%{query}%', f'%{query}%'))
        
        results = []
        for eid, name, typ, desc in cur.fetchall():
            cur.execute("""
                SELECT n.entity_name, n.entity_type, e.relationship_type
                FROM graph_edges e
                JOIN graph_nodes n ON n.id = e.target_node_id
                WHERE e.source_node_id = %s
            """, (eid,))
            
            connections = [
                {'name': c[0], 'type': c[1], 'rel': c[2]}
                for c in cur.fetchall()
            ]
            
            results.append({
                'entity': name,
                'type': typ,
                'description': desc,
                'connections': connections
            })
        
        cur.close()
        conn.close()
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/graph/batch-insert', methods=['POST'])
def batch_insert():
    try:
        data = request.json
        entities = data.get('entities', [])
        relationships = data.get('relationships', [])

        conn = psycopg2.connect(**DB)
        cur = conn.cursor()

        entity_ids = {}
        for entity in entities:
            cur.execute("""
                INSERT INTO graph_nodes (entity_name, entity_type, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (entity_name) DO UPDATE
                SET description = COALESCE(EXCLUDED.description, graph_nodes.description)
                RETURNING id, entity_name
            """, (entity['name'], entity.get('type'), entity.get('description')))

            result = cur.fetchone()
            entity_ids[result[1]] = result[0]

        edges_created = 0
        for rel in relationships:
            source = rel['source']
            target = rel['target']

            if source not in entity_ids:
                cur.execute("SELECT id FROM graph_nodes WHERE entity_name = %s", (source,))
                r = cur.fetchone()
                if r:
                    entity_ids[source] = r[0]

            if target not in entity_ids:
                cur.execute("SELECT id FROM graph_nodes WHERE entity_name = %s", (target,))
                r = cur.fetchone()
                if r:
                    entity_ids[target] = r[0]

            if source in entity_ids and target in entity_ids:
                cur.execute("""
                    INSERT INTO graph_edges (source_node_id, target_node_id, relationship_type, weight)
                    SELECT %s, %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM graph_edges 
                        WHERE source_node_id = %s AND target_node_id = %s
                    )
                """, (entity_ids[source], entity_ids[target], 
                     rel.get('type', 'related_to'), rel.get('weight', 1.0),
                     entity_ids[source], entity_ids[target]))
                edges_created += cur.rowcount

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'status': 'success',
            'entities_processed': len(entities),
            'edges_created': edges_created
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/graph/batch-insert-with-embeddings', methods=['POST'])
def batch_insert_with_embeddings():
    """Insert nodes with local embeddings for semantic search"""
    try:
        data = request.json
        entities = data.get('entities', [])
        relationships = data.get('relationships', [])
        
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        entity_ids = {}
        embeddings_created = 0
        
        for entity in entities:
            # Generate embedding from entity name + description
            text_for_embedding = f"{entity['name']} {entity.get('type', '')} {entity.get('description', '')}"
            embedding = get_embedding(text_for_embedding)
            
            if embedding:
                cur.execute("""
                    INSERT INTO graph_nodes (entity_name, entity_type, description, embedding)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (entity_name) DO UPDATE
                    SET description = COALESCE(EXCLUDED.description, graph_nodes.description),
                        embedding = EXCLUDED.embedding
                    RETURNING id, entity_name
                """, (entity['name'], entity.get('type'), entity.get('description'), embedding))
                embeddings_created += 1
            else:
                cur.execute("""
                    INSERT INTO graph_nodes (entity_name, entity_type, description)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (entity_name) DO UPDATE
                    SET description = COALESCE(EXCLUDED.description, graph_nodes.description)
                    RETURNING id, entity_name
                """, (entity['name'], entity.get('type'), entity.get('description')))
            
            result = cur.fetchone()
            entity_ids[result[1]] = result[0]
        
        # Insert relationships
        edges_created = 0
        for rel in relationships:
            source = rel['source']
            target = rel['target']
            
            if source not in entity_ids:
                cur.execute("SELECT id FROM graph_nodes WHERE entity_name = %s", (source,))
                r = cur.fetchone()
                if r:
                    entity_ids[source] = r[0]
            
            if target not in entity_ids:
                cur.execute("SELECT id FROM graph_nodes WHERE entity_name = %s", (target,))
                r = cur.fetchone()
                if r:
                    entity_ids[target] = r[0]
            
            if source in entity_ids and target in entity_ids:
                cur.execute("""
                    INSERT INTO graph_edges (source_node_id, target_node_id, relationship_type, weight)
                    SELECT %s, %s, %s, %s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM graph_edges 
                        WHERE source_node_id = %s AND target_node_id = %s
                    )
                """, (entity_ids[source], entity_ids[target], 
                     rel.get('type', 'related_to'), rel.get('weight', 1.0),
                     entity_ids[source], entity_ids[target]))
                edges_created += cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'entities_processed': len(entities),
            'embeddings_created': embeddings_created,
            'edges_created': edges_created
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/graph/semantic-search', methods=['POST'])
def semantic_search():
    """Search using vector similarity + graph traversal"""
    try:
        data = request.json
        query = data.get('query', '')
        limit = data.get('limit', 5)
        
        # Generate query embedding
        query_embedding = get_embedding(query)
        if not query_embedding:
            return jsonify({'error': 'Failed to generate embedding'}), 500
        
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        # Vector similarity search
        cur.execute("""
            SELECT 
                id,
                entity_name,
                entity_type,
                description,
                1 - (embedding <=> %s::vector) as similarity
            FROM graph_nodes
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """, (query_embedding, query_embedding, limit))
        
        results = []
        for node_id, name, typ, desc, similarity in cur.fetchall():
            # Get graph connections
            cur.execute("""
                SELECT n.entity_name, n.entity_type, e.relationship_type
                FROM graph_edges e
                JOIN graph_nodes n ON n.id = e.target_node_id
                WHERE e.source_node_id = %s
            """, (node_id,))
            
            connections = [
                {'name': c[0], 'type': c[1], 'rel': c[2]}
                for c in cur.fetchall()
            ]
            
            results.append({
                'entity': name,
                'type': typ,
                'description': desc,
                'similarity': float(similarity),
                'connections': connections
            })
        
        cur.close()
        conn.close()
        
        return jsonify({'results': results})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/graph/add-embeddings-to-existing', methods=['POST'])
def add_embeddings_to_existing():
    """Add embeddings to nodes that don't have them"""
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        # Get nodes without embeddings
        cur.execute("""
            SELECT id, entity_name, entity_type, description
            FROM graph_nodes
            WHERE embedding IS NULL
            LIMIT 100
        """)
        
        nodes = cur.fetchall()
        embeddings_added = 0
        
        for node_id, name, typ, desc in nodes:
            text = f"{name} {typ or ''} {desc or ''}"
            embedding = get_embedding(text)
            
            if embedding:
                cur.execute("""
                    UPDATE graph_nodes
                    SET embedding = %s
                    WHERE id = %s
                """, (embedding, node_id))
                embeddings_added += 1
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'embeddings_added': embeddings_added,
            'nodes_processed': len(nodes)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/graph/visualize', methods=['GET'])
def visualize():
    """Get graph data for visualization"""
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, entity_name, entity_type, description
            FROM graph_nodes
            ORDER BY created_at DESC
            LIMIT 1000
        """)
        
        nodes = [
            {
                'id': str(row[0]),
                'label': row[1],
                'type': row[2] or 'Unknown',
                'description': row[3] or ''
            }
            for row in cur.fetchall()
        ]
        
        node_ids = [n['id'] for n in nodes]
        if node_ids:
            placeholders = ','.join(['%s'] * len(node_ids))
            cur.execute(f"""
                SELECT 
                    e.source_node_id,
                    e.target_node_id,
                    e.relationship_type,
                    e.weight
                FROM graph_edges e
                WHERE e.source_node_id IN ({placeholders})
                   OR e.target_node_id IN ({placeholders})
                LIMIT 2000
            """, node_ids + node_ids)
            
            edges = [
                {
                    'source': str(row[0]),
                    'target': str(row[1]),
                    'label': row[2],
                    'weight': float(row[3]) if row[3] else 1.0
                }
                for row in cur.fetchall()
            ]
        else:
            edges = []
        
        cur.close()
        conn.close()
        
        return jsonify({
            'nodes': nodes,
            'edges': edges,
            'stats': {
                'node_count': len(nodes),
                'edge_count': len(edges)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/graph/deduplicate', methods=['POST'])
def deduplicate():
    """Find and merge duplicate entities"""
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                LOWER(entity_name) as name_lower,
                id,
                entity_name
            FROM graph_nodes
            ORDER BY LOWER(entity_name), created_at
        """)
        
        rows = cur.fetchall()
        merged = 0
        duplicates = {}
        
        for name_lower, node_id, entity_name in rows:
            if name_lower not in duplicates:
                duplicates[name_lower] = []
            duplicates[name_lower].append((node_id, entity_name))
        
        for name_lower, nodes in duplicates.items():
            if len(nodes) > 1:
                keep_id = nodes[0][0]
                
                for merge_id, merge_name in nodes[1:]:
                    cur.execute("""
                        UPDATE graph_edges 
                        SET source_node_id = %s 
                        WHERE source_node_id = %s
                    """, (keep_id, merge_id))
                    
                    cur.execute("""
                        UPDATE graph_edges 
                        SET target_node_id = %s 
                        WHERE target_node_id = %s
                    """, (keep_id, merge_id))
                    
                    cur.execute("DELETE FROM graph_nodes WHERE id = %s", (merge_id,))
                    merged += 1
        
        cur.execute("""
            DELETE FROM graph_edges 
            WHERE source_node_id = target_node_id
        """)
        self_refs = cur.rowcount
        
        conn.commit()
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'entities_merged': merged,
            'self_references_removed': self_refs
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)
