"""
RAG-based Intent Matcher
Uses vector embeddings to match user queries to intents with semantic similarity.
"""

import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple, Optional
from app.core.logger import get_logger

log = get_logger("intent_rag")


class IntentRAG:
    """
    RAG-based intent matching using vector embeddings.
    Provides semantic similarity matching for better intent recognition.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG intent matcher.
        
        Args:
            model_name: Sentence transformer model name
        """
        self.model = SentenceTransformer(model_name)
        self.client = chromadb.PersistentClient(path="./chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="intents",
            metadata={"hnsw:space": "cosine"}
        )
        self._initialize_intents()
    
    def _initialize_intents(self):
        """
        Initialize the intent registry with embeddings.
        This creates the vector database with all known intents and their examples.
        """
        intents = self._get_intent_registry()
        
        # Clear existing collection
        try:
            self.client.delete_collection("intents")
            self.collection = self.client.create_collection(
                name="intents",
                metadata={"hnsw:space": "cosine"}
            )
        except:
            pass
        
        # Add intents to collection
        for intent_data in intents:
            intent_name = intent_data["intent"]
            examples = intent_data["examples"]
            description = intent_data["description"]
            
            # Generate embeddings for all examples
            embeddings = self.model.encode(examples).tolist()
            
            # Add to collection
            self.collection.add(
                documents=examples,
                embeddings=embeddings,
                metadatas=[{"intent": intent_name, "description": description}] * len(examples),
                ids=[f"{intent_name}_{i}" for i in range(len(examples))]
            )
        
        log.info(f"Initialized RAG with {len(intents)} intents and {sum(len(i['examples']) for i in intents)} examples")
    
    def _get_intent_registry(self) -> List[Dict]:
        """
        Get the complete intent registry with user-friendly examples.
        
        Returns:
            List of intent dictionaries with examples
        """
        return [
            {
                "intent": "GREETING",
                "description": "Greeting the assistant",
                "examples": [
                    "hello",
                    "hi there",
                    "hey",
                    "good morning",
                    "good afternoon",
                    "good evening",
                    "hi orbit",
                    "hello orbit",
                    "hey orbit",
                    "what's up",
                    "how are you",
                    "howdy"
                ]
            },
            {
                "intent": "LIST_USERS",
                "description": "List all users in the system",
                "examples": [
                    "show me all users",
                    "list all users",
                    "who are the users",
                    "display users",
                    "get user list",
                    "show users",
                    "all users",
                    "user list",
                    "who works here",
                    "team members",
                    "employees list"
                ]
            },
            {
                "intent": "REGISTER_USER",
                "description": "Register a new user",
                "examples": [
                    "add a new user",
                    "register user",
                    "create user",
                    "add employee",
                    "hire someone",
                    "new user registration",
                    "sign up user",
                    "add team member",
                    "create account for",
                    "register employee"
                ]
            },
            {
                "intent": "DELETE_USER",
                "description": "Delete a user from the system",
                "examples": [
                    "remove user",
                    "delete user",
                    "terminate user",
                    "fire employee",
                    "remove account",
                    "delete account",
                    "get rid of user",
                    "remove employee"
                ]
            },
            {
                "intent": "UPDATE_USER",
                "description": "Update user details",
                "examples": [
                    "change user email",
                    "update user",
                    "modify user details",
                    "edit user information",
                    "change user info",
                    "update employee",
                    "modify employee details"
                ]
            },
            {
                "intent": "LIST_PROJECTS",
                "description": "List all projects",
                "examples": [
                    "show all projects",
                    "list projects",
                    "what projects do we have",
                    "display projects",
                    "get project list",
                    "show projects",
                    "all projects",
                    "project list",
                    "current projects"
                ]
            },
            {
                "intent": "CREATE_PROJECT",
                "description": "Create a new project",
                "examples": [
                    "create a project",
                    "start a project",
                    "new project",
                    "add project",
                    "begin project",
                    "set up project",
                    "initiate project"
                ]
            },
            {
                "intent": "DELETE_PROJECT",
                "description": "Delete a project",
                "examples": [
                    "remove project",
                    "delete project",
                    "cancel project",
                    "remove project",
                    "terminate project"
                ]
            },
            {
                "intent": "START_PROJECT",
                "description": "Start a project",
                "examples": [
                    "start project",
                    "launch project",
                    "begin project",
                    "kick off project",
                    "initiate project"
                ]
            },
            {
                "intent": "LIST_TASKS",
                "description": "List all tasks",
                "examples": [
                    "show all tasks",
                    "list tasks",
                    "what tasks do we have",
                    "display tasks",
                    "get task list",
                    "show tasks",
                    "all tasks",
                    "task list",
                    "current tasks"
                ]
            },
            {
                "intent": "CREATE_TASK",
                "description": "Create a new task",
                "examples": [
                    "create a task",
                    "add task",
                    "new task",
                    "add to-do",
                    "create to-do item",
                    "add work item"
                ]
            },
            {
                "intent": "DELETE_TASK",
                "description": "Delete a task",
                "examples": [
                    "remove task",
                    "delete task",
                    "cancel task",
                    "remove to-do",
                    "delete to-do"
                ]
            },
            {
                "intent": "CLOSE_TASK",
                "description": "Mark a task as complete",
                "examples": [
                    "complete task",
                    "finish task",
                    "close task",
                    "mark task done",
                    "task completed",
                    "done with task",
                    "finish to-do",
                    "complete to-do"
                ]
            },
            {
                "intent": "ASSIGN_TASK",
                "description": "Assign a task to someone",
                "examples": [
                    "assign task to",
                    "give task to",
                    "delegate task",
                    "assign work to",
                    "give work to someone"
                ]
            },
            {
                "intent": "LIST_DEPARTMENTS",
                "description": "List all departments",
                "examples": [
                    "show all departments",
                    "list departments",
                    "what departments do we have",
                    "display departments",
                    "get department list",
                    "show departments",
                    "all departments",
                    "department list",
                    "teams"
                ]
            },
            {
                "intent": "CREATE_DEPARTMENT",
                "description": "Create a new department",
                "examples": [
                    "create a department",
                    "add department",
                    "new department",
                    "set up department",
                    "establish department",
                    "create team"
                ]
            },
            {
                "intent": "DELETE_DEPARTMENT",
                "description": "Delete a department",
                "examples": [
                    "remove department",
                    "delete department",
                    "disband department",
                    "remove team"
                ]
            },
            {
                "intent": "LIST_ROLES",
                "description": "List all roles",
                "examples": [
                    "show all roles",
                    "list roles",
                    "what roles do we have",
                    "display roles",
                    "get role list",
                    "show roles",
                    "all roles",
                    "role list",
                    "permissions"
                ]
            },
            {
                "intent": "LIST_MY_INFO",
                "description": "Show user's own information",
                "examples": [
                    "who am i",
                    "my profile",
                    "show my info",
                    "my account",
                    "my details",
                    "about me",
                    "my information"
                ]
            },
            {
                "intent": "LIST_MY_TASKS",
                "description": "List tasks assigned to the user",
                "examples": [
                    "show my tasks",
                    "my tasks",
                    "what are my tasks",
                    "tasks assigned to me",
                    "my to-dos",
                    "my work",
                    "my assignments"
                ]
            },
            {
                "intent": "SEND_EMAIL",
                "description": "Send an email",
                "examples": [
                    "send email",
                    "send mail",
                    "email someone",
                    "send message",
                    "compose email"
                ]
            },
            {
                "intent": "LIST_MEETINGS",
                "description": "List all meetings",
                "examples": [
                    "show all meetings",
                    "list meetings",
                    "upcoming meetings",
                    "scheduled meetings",
                    "meeting schedule",
                    "calendar"
                ]
            },
            {
                "intent": "CREATE_MEETING",
                "description": "Create a new meeting",
                "examples": [
                    "schedule a meeting",
                    "create meeting",
                    "set up meeting",
                    "book meeting",
                    "arrange meeting"
                ]
            },
            {
                "intent": "DELETE_MEETING",
                "description": "Delete a meeting",
                "examples": [
                    "cancel meeting",
                    "delete meeting",
                    "remove meeting"
                ]
            },
            {
                "intent": "LIST_MANAGEABLE_TASKS",
                "description": "List what the assistant can do",
                "examples": [
                    "what can you do",
                    "help",
                    "capabilities",
                    "what are your features",
                    "show me what you can do",
                    "your abilities",
                    "assistant features"
                ]
            },
            {
                "intent": "HIRE_CANDIDATE",
                "description": "Hire a new candidate",
                "examples": [
                    "hire candidate",
                    "onboard new employee",
                    "hire someone",
                    "recruit candidate",
                    "new hire"
                ]
            }
        ]
    
    def match_intent(self, query: str, top_k: int = 3) -> Optional[Dict]:
        """
        Match user query to intent using semantic similarity.
        
        Args:
            query: User's natural language query
            top_k: Number of top matches to return
            
        Returns:
            Dictionary with matched intent and confidence, or None if no match
        """
        try:
            # Generate embedding for query
            query_embedding = self.model.encode([query]).tolist()
            
            # Search for similar intents
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k
            )
            
            if not results["documents"] or not results["documents"][0]:
                return None
            
            # Get the best match
            best_match_idx = 0
            best_distance = results["distances"][0][best_match_idx]
            
            # Convert distance to confidence (cosine similarity)
            confidence = 1 - best_distance
            
            # Get intent from metadata
            intent = results["metadatas"][0][best_match_idx]["intent"]
            description = results["metadatas"][0][best_match_idx]["description"]
            
            # Only return if confidence is above threshold
            if confidence >= 0.7:
                log.info(f"RAG matched query '{query}' to intent '{intent}' with confidence {confidence:.2f}")
                return {
                    "intent": intent,
                    "confidence": confidence,
                    "description": description,
                    "method": "rag"
                }
            else:
                log.info(f"RAG confidence {confidence:.2f} below threshold for query '{query}'")
                return None
                
        except Exception as e:
            log.error(f"Error in RAG intent matching: {str(e)}")
            return None
    
    def add_custom_intent(self, intent: str, description: str, examples: List[str]):
        """
        Add a custom intent to the registry.
        
        Args:
            intent: Intent name
            description: Intent description
            examples: List of example phrases
        """
        try:
            # Generate embeddings
            embeddings = self.model.encode(examples).tolist()
            
            # Add to collection
            self.collection.add(
                documents=examples,
                embeddings=embeddings,
                metadatas=[{"intent": intent, "description": description}] * len(examples),
                ids=[f"{intent}_{i}" for i in range(len(examples))]
            )
            
            log.info(f"Added custom intent '{intent}' with {len(examples)} examples")
            
        except Exception as e:
            log.error(f"Error adding custom intent: {str(e)}")


# Singleton instance
intent_rag = IntentRAG()
