from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Load the model once when the server starts
print("Loading AI Model (all-MiniLM-L6-v2)...")
model = SentenceTransformer('all-MiniLM-L6-v2')

def find_matches(new_item_data, db_items):
    """
    new_item_data: dict containing 'title', 'description', 'type', 'category'
    db_items: list of Item objects from the database
    """
    potential_matches = []
    
    # 1. Filter candidates: Only compare LOST vs FOUND
    candidates = [item for item in db_items if item.type != new_item_data['type']]
    
    if not candidates:
        return []

    # 2. Prepare texts (Title + Description + Category)
    # Adding 'category' helps the AI distinguish between a 'Phone' and a 'Phone Case'
    target_text = f"{new_item_data['title']} {new_item_data['description']} {new_item_data['category']}"
    candidate_texts = [f"{item.title} {item.description} {item.category}" for item in candidates]

    # 3. Generate Embeddings
    target_embedding = model.encode([target_text])
    candidate_embeddings = model.encode(candidate_texts)

    # 4. Calculate Similarity
    scores = cosine_similarity(target_embedding, candidate_embeddings)[0]

    # 5. Filter and Format
    for i, score in enumerate(scores):
        # Threshold set to 0.30 (30%) to catch partial/little matches
        if score > 0.30:  
            potential_matches.append({
                'item': candidates[i],
                'score': score
            })
    
    # 6. Sort by highest score first
    sorted_matches = sorted(potential_matches, key=lambda x: x['score'], reverse=True)
    
    # 7. Return ONLY the Item objects (Extract them from the dict)
    # This ensures your app.py loop (for match in matches) works correctly
    return [match['item'] for match in sorted_matches]