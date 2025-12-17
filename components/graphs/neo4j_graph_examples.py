"""
Example Cypher queries for Neo4j Graph Component

This file contains example Cypher queries that can be used with the Neo4jGraphComponent
to create, populate, and query a graph database.

Example Graph: Knowledge Graph about Technology and People
"""

# ============================================================================
# SETUP: Create nodes and relationships
# ============================================================================

CREATE_KNOWLEDGE_GRAPH = """
// Create a knowledge graph about technology, people, and companies

// Create Person nodes
CREATE (alice:Person {name: "Alice", age: 30, role: "Data Scientist"})
CREATE (bob:Person {name: "Bob", age: 35, role: "Software Engineer"})
CREATE (charlie:Person {name: "Charlie", age: 28, role: "ML Engineer"})
CREATE (diana:Person {name: "Diana", age: 32, role: "Data Engineer"})

// Create Company nodes
CREATE (techcorp:Company {name: "TechCorp", industry: "Technology", founded: 2010})
CREATE (datainc:Company {name: "DataInc", industry: "Data Analytics", founded: 2015})
CREATE (aiworks:Company {name: "AIWorks", industry: "Artificial Intelligence", founded: 2018})

// Create Technology nodes
CREATE (python:Technology {name: "Python", type: "Programming Language", popularity: 95})
CREATE (neo4j:Technology {name: "Neo4j", type: "Graph Database", popularity: 80})
CREATE (ml:Technology {name: "Machine Learning", type: "Field", popularity: 90})
CREATE (nlp:Technology {name: "NLP", type: "Field", popularity: 85})

// Create relationships: People work at Companies
CREATE (alice)-[:WORKS_AT {since: 2020, position: "Senior Data Scientist"}]->(techcorp)
CREATE (bob)-[:WORKS_AT {since: 2019, position: "Lead Engineer"}]->(techcorp)
CREATE (charlie)-[:WORKS_AT {since: 2021, position: "ML Engineer"}]->(aiworks)
CREATE (diana)-[:WORKS_AT {since: 2022, position: "Data Engineer"}]->(datainc)

// Create relationships: People know each other
CREATE (alice)-[:KNOWS {since: 2018, relationship: "colleague"}]->(bob)
CREATE (bob)-[:KNOWS {since: 2019, relationship: "friend"}]->(charlie)
CREATE (alice)-[:KNOWS {since: 2020, relationship: "mentor"}]->(diana)

// Create relationships: People use Technologies
CREATE (alice)-[:USES {proficiency: "expert", years: 5}]->(python)
CREATE (alice)-[:USES {proficiency: "intermediate", years: 2}]->(neo4j)
CREATE (alice)-[:USES {proficiency: "expert", years: 6}]->(ml)
CREATE (bob)-[:USES {proficiency: "expert", years: 8}]->(python)
CREATE (charlie)-[:USES {proficiency: "expert", years: 4}]->(ml)
CREATE (charlie)-[:USES {proficiency: "advanced", years: 3}]->(nlp)
CREATE (diana)-[:USES {proficiency: "advanced", years: 3}]->(python)
CREATE (diana)-[:USES {proficiency: "intermediate", years: 1}]->(neo4j)

// Create relationships: Companies use Technologies
CREATE (techcorp)-[:USES_TECH {since: 2015}]->(python)
CREATE (techcorp)-[:USES_TECH {since: 2020}]->(neo4j)
CREATE (aiworks)-[:USES_TECH {since: 2018}]->(ml)
CREATE (aiworks)-[:USES_TECH {since: 2019}]->(nlp)
CREATE (datainc)-[:USES_TECH {since: 2016}]->(python)
"""

# ============================================================================
# QUERIES: Read and analyze the graph
# ============================================================================

# Query 1: Find all people and their companies
QUERY_ALL_PEOPLE_AND_COMPANIES = """
MATCH (p:Person)-[r:WORKS_AT]->(c:Company)
RETURN p.name AS person, c.name AS company, r.position AS position, r.since AS since
ORDER BY p.name
"""

# Query 2: Find people who know each other
QUERY_PEOPLE_CONNECTIONS = """
MATCH (p1:Person)-[r:KNOWS]->(p2:Person)
RETURN p1.name AS person1, p2.name AS person2, r.relationship AS relationship, r.since AS since
ORDER BY r.since
"""

# Query 3: Find technologies used by each person
QUERY_PERSON_TECHNOLOGIES = """
MATCH (p:Person)-[r:USES]->(t:Technology)
RETURN p.name AS person, t.name AS technology, r.proficiency AS proficiency, r.years AS years
ORDER BY p.name, r.years DESC
"""

# Query 4: Find people who work at the same company
QUERY_COLLEAGUES = """
MATCH (p1:Person)-[:WORKS_AT]->(c:Company)<-[:WORKS_AT]-(p2:Person)
WHERE p1 <> p2
RETURN c.name AS company, p1.name AS person1, p2.name AS person2
ORDER BY c.name, p1.name
"""

# Query 5: Find the most connected person (degree centrality)
QUERY_MOST_CONNECTED = """
MATCH (p:Person)
OPTIONAL MATCH (p)-[r1:KNOWS]->()
OPTIONAL MATCH ()-[r2:KNOWS]->(p)
OPTIONAL MATCH (p)-[r3:WORKS_AT]->()
WITH p, COUNT(DISTINCT r1) + COUNT(DISTINCT r2) + COUNT(DISTINCT r3) AS connections
RETURN p.name AS person, p.role AS role, connections
ORDER BY connections DESC
LIMIT 5
"""

# Query 6: Find path between two people (shortest path)
QUERY_PATH_BETWEEN_PEOPLE = """
MATCH path = shortestPath(
  (p1:Person {name: "Alice"})-[*]-(p2:Person {name: "Charlie"})
)
RETURN path
LIMIT 1
"""

# Query 7: Find technologies used by people at a specific company
QUERY_COMPANY_TECHNOLOGIES = """
MATCH (c:Company {name: "TechCorp"})<-[:WORKS_AT]-(p:Person)-[:USES]->(t:Technology)
RETURN DISTINCT t.name AS technology, COUNT(p) AS users, 
       COLLECT(DISTINCT p.name) AS people
ORDER BY users DESC
"""

# Query 8: Find people who use a specific technology
QUERY_TECHNOLOGY_USERS = """
MATCH (p:Person)-[r:USES]->(t:Technology {name: "Python"})
RETURN p.name AS person, p.role AS role, r.proficiency AS proficiency, r.years AS years
ORDER BY r.years DESC
"""

# Query 9: Find companies and their employees count
QUERY_COMPANY_STATS = """
MATCH (c:Company)
OPTIONAL MATCH (p:Person)-[:WORKS_AT]->(c)
RETURN c.name AS company, c.industry AS industry, COUNT(p) AS employees
ORDER BY employees DESC
"""

# Query 10: Find all relationships for a specific person
QUERY_PERSON_NETWORK = """
MATCH (p:Person {name: "Alice"})-[r]-(connected)
RETURN TYPE(r) AS relationship_type, 
       LABELS(connected)[0] AS connected_type,
       connected.name AS connected_name,
       r
ORDER BY relationship_type
"""

# ============================================================================
# CLEANUP: Remove all data (use with caution!)
# ============================================================================

DELETE_ALL_DATA = """
MATCH (n)
DETACH DELETE n
"""

# ============================================================================
# EXAMPLE: Simple social network
# ============================================================================

CREATE_SOCIAL_NETWORK = """
// Create a simple social network graph

// Create users
CREATE (user1:User {id: 1, name: "John", email: "john@example.com"})
CREATE (user2:User {id: 2, name: "Jane", email: "jane@example.com"})
CREATE (user3:User {id: 3, name: "Bob", email: "bob@example.com"})
CREATE (user4:User {id: 4, name: "Alice", email: "alice@example.com"})

// Create posts
CREATE (post1:Post {id: 1, title: "Hello World", content: "My first post", created: "2024-01-15"})
CREATE (post2:Post {id: 2, title: "Neo4j is great", content: "Learning graph databases", created: "2024-01-20"})
CREATE (post3:Post {id: 3, title: "Python tips", content: "Some Python tips", created: "2024-01-25"})

// Create relationships: Users follow each other
CREATE (user1)-[:FOLLOWS {since: "2024-01-01"}]->(user2)
CREATE (user1)-[:FOLLOWS {since: "2024-01-05"}]->(user3)
CREATE (user2)-[:FOLLOWS {since: "2024-01-10"}]->(user3)
CREATE (user2)-[:FOLLOWS {since: "2024-01-12"}]->(user4)
CREATE (user3)-[:FOLLOWS {since: "2024-01-15"}]->(user1)

// Create relationships: Users create posts
CREATE (user1)-[:CREATED]->(post1)
CREATE (user2)-[:CREATED]->(post2)
CREATE (user3)-[:CREATED]->(post3)

// Create relationships: Users like posts
CREATE (user2)-[:LIKES {timestamp: "2024-01-15T10:00:00"}]->(post1)
CREATE (user3)-[:LIKES {timestamp: "2024-01-15T11:00:00"}]->(post1)
CREATE (user1)-[:LIKES {timestamp: "2024-01-20T09:00:00"}]->(post2)
CREATE (user4)-[:LIKES {timestamp: "2024-01-20T10:00:00"}]->(post2)
"""

QUERY_SOCIAL_NETWORK = """
// Find posts and their authors with like count
MATCH (u:User)-[:CREATED]->(p:Post)
OPTIONAL MATCH (liker:User)-[:LIKES]->(p)
RETURN p.title AS post, u.name AS author, COUNT(liker) AS likes
ORDER BY likes DESC
"""

# ============================================================================
# EXAMPLE: Product recommendation graph
# ============================================================================

CREATE_PRODUCT_GRAPH = """
// Create a product recommendation graph

// Create products
CREATE (p1:Product {id: 1, name: "Laptop", category: "Electronics", price: 999.99})
CREATE (p2:Product {id: 2, name: "Mouse", category: "Electronics", price: 29.99})
CREATE (p3:Product {id: 3, name: "Keyboard", category: "Electronics", price: 79.99})
CREATE (p4:Product {id: 4, name: "Monitor", category: "Electronics", price: 299.99})
CREATE (p5:Product {id: 5, name: "Headphones", category: "Audio", price: 149.99})

// Create customers
CREATE (c1:Customer {id: 1, name: "Customer A", email: "a@example.com"})
CREATE (c2:Customer {id: 2, name: "Customer B", email: "b@example.com"})
CREATE (c3:Customer {id: 3, name: "Customer C", email: "c@example.com"})

// Create purchases
CREATE (c1)-[:PURCHASED {date: "2024-01-10", quantity: 1}]->(p1)
CREATE (c1)-[:PURCHASED {date: "2024-01-10", quantity: 1}]->(p2)
CREATE (c1)-[:PURCHASED {date: "2024-01-15", quantity: 1}]->(p3)
CREATE (c2)-[:PURCHASED {date: "2024-01-12", quantity: 1}]->(p1)
CREATE (c2)-[:PURCHASED {date: "2024-01-12", quantity: 1}]->(p4)
CREATE (c3)-[:PURCHASED {date: "2024-01-20", quantity: 1}]->(p2)
CREATE (c3)-[:PURCHASED {date: "2024-01-20", quantity: 1}]->(p3)

// Create product relationships (complementary products)
CREATE (p1)-[:COMPATIBLE_WITH]->(p2)
CREATE (p1)-[:COMPATIBLE_WITH]->(p3)
CREATE (p1)-[:COMPATIBLE_WITH]->(p4)
CREATE (p2)-[:OFTEN_BOUGHT_WITH]->(p3)
"""

QUERY_PRODUCT_RECOMMENDATIONS = """
// Find products often bought together
MATCH (c:Customer)-[:PURCHASED]->(p1:Product),
      (c)-[:PURCHASED]->(p2:Product)
WHERE p1 <> p2
RETURN p1.name AS product1, p2.name AS product2, COUNT(c) AS times_bought_together
ORDER BY times_bought_together DESC
LIMIT 10
"""

