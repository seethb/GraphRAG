-- Create the demo database
CREATE DATABASE graphrag;

-- Connect to demo database
\c graphrag

-- Install the pgvector extension
CREATE EXTENSION vector;

-- Drop existing tables if any
DROP TABLE IF EXISTS graph_edges CASCADE;
DROP TABLE IF EXISTS graph_nodes CASCADE;

-- Create graph_nodes table
CREATE TABLE graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name TEXT UNIQUE NOT NULL,
    entity_type TEXT,
    description TEXT,
    embedding vector(384),
    properties JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create graph_edges table
CREATE TABLE graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id UUID NOT NULL REFERENCES graph_nodes(id) ON DELETE CASCADE,
    relationship_type VARCHAR(100) NOT NULL,
    properties JSONB DEFAULT '{}',
    weight FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_nodes_name ON graph_nodes(entity_name);
CREATE INDEX idx_nodes_type ON graph_nodes(entity_type);
CREATE INDEX idx_edges_source ON graph_edges(source_node_id);
CREATE INDEX idx_edges_target ON graph_edges(target_node_id);
CREATE INDEX idx_edges_relationship ON graph_edges(relationship_type);

-- Insert sample data
/*
INSERT INTO graph_nodes (entity_name, entity_type, description) VALUES
('YugabyteDB', 'Database', 'Distributed SQL database with PostgreSQL compatibility for global applications'),
('PostgreSQL', 'Database', 'Advanced open-source relational database system'),
('Dify', 'Platform', 'LLM application development platform with workflow orchestration'),
('GraphRAG', 'Technology', 'Graph-based Retrieval Augmented Generation combining knowledge graphs with LLMs'),
('Python', 'Language', 'High-level programming language widely used in AI and data science'),
('Redis', 'Cache', 'In-memory data structure store used for caching and message queuing'),
('Docker', 'Platform', 'Containerization platform for deploying applications'),
('LLM', 'Technology', 'Large Language Models for natural language processing'),
('RAG', 'Technology', 'Retrieval Augmented Generation for enhanced AI responses');

-- Create relationships
INSERT INTO graph_edges (source_node_id, target_node_id, relationship_type, weight)
VALUES
    ((SELECT id FROM graph_nodes WHERE entity_name = 'YugabyteDB'),
     (SELECT id FROM graph_nodes WHERE entity_name = 'PostgreSQL'),
     'compatible_with', 0.9),
    
    ((SELECT id FROM graph_nodes WHERE entity_name = 'Dify'),
     (SELECT id FROM graph_nodes WHERE entity_name = 'Python'),
     'built_with', 1.0),
    
    ((SELECT id FROM graph_nodes WHERE entity_name = 'Dify'),
     (SELECT id FROM graph_nodes WHERE entity_name = 'Redis'),
     'uses', 0.8),
    
    ((SELECT id FROM graph_nodes WHERE entity_name = 'Dify'),
     (SELECT id FROM graph_nodes WHERE entity_name = 'Docker'),
     'deployed_with', 0.7),
    
    ((SELECT id FROM graph_nodes WHERE entity_name = 'GraphRAG'),
     (SELECT id FROM graph_nodes WHERE entity_name = 'LLM'),
     'uses', 1.0),
    
    ((SELECT id FROM graph_nodes WHERE entity_name = 'GraphRAG'),
     (SELECT id FROM graph_nodes WHERE entity_name = 'RAG'),
     'extends', 0.9),
    
    ((SELECT id FROM graph_nodes WHERE entity_name = 'Dify'),
     (SELECT id FROM graph_nodes WHERE entity_name = 'YugabyteDB'),
     'stores_data_in', 0.8);

-- Verify data
SELECT 'Created ' || COUNT(*) || ' nodes' as result FROM graph_nodes;
SELECT 'Created ' || COUNT(*) || ' edges' as result FROM graph_edges;
*/