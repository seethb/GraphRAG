# Just the fixed deduplicate function - we'll merge it

@app.route('/graph/deduplicate', methods=['POST'])
def deduplicate():
    """Find and merge duplicate entities"""
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        
        # Find duplicates (case-insensitive)
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
        
        # Group duplicates
        for name_lower, node_id, entity_name in rows:
            if name_lower not in duplicates:
                duplicates[name_lower] = []
            duplicates[name_lower].append((node_id, entity_name))
        
        # Merge duplicates
        for name_lower, nodes in duplicates.items():
            if len(nodes) > 1:
                # Keep the first one
                keep_id = nodes[0][0]
                
                # Merge others into it
                for merge_id, merge_name in nodes[1:]:
                    # Update edges pointing from this node
                    cur.execute("""
                        UPDATE graph_edges 
                        SET source_node_id = %s 
                        WHERE source_node_id = %s
                    """, (keep_id, merge_id))
                    
                    # Update edges pointing to this node
                    cur.execute("""
                        UPDATE graph_edges 
                        SET target_node_id = %s 
                        WHERE target_node_id = %s
                    """, (keep_id, merge_id))
                    
                    # Delete the duplicate node
                    cur.execute("DELETE FROM graph_nodes WHERE id = %s", (merge_id,))
                    merged += 1
        
        # Remove self-referencing edges
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
