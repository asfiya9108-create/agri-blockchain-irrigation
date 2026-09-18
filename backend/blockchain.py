import hashlib
import json
import time
from datetime import datetime
from typing import List, Dict, Any

class Block:
    def _init_(self, index: int, transactions: List[Dict], timestamp: float, previous_hash: str):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = 0
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty: int = 2) -> None:
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()

class AgriBlockchain:
    def _init_(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[Dict] = []
        self.difficulty = 2
        self.create_genesis_block()

    def create_genesis_block(self) -> None:
        genesis_block = Block(0, [{
            "type": "genesis",
            "timestamp": time.time(),
            "data": "Genesis Block - Agriculture Irrigation System"
        }], time.time(), "0")
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, transaction: Dict) -> int:
        required_fields = ["farmer_id", "soil_moisture", "water_usage", "status"]
        if not all(field in transaction for field in required_fields):
            raise ValueError("Missing required transaction fields")
        
        transaction["timestamp"] = time.time()
        self.pending_transactions.append(transaction)
        return self.get_latest_block().index + 1

    def mine_pending_transactions(self, miner_address: str) -> None:
        if not self.pending_transactions:
            return
        
        block = Block(
            len(self.chain),
            self.pending_transactions,
            time.time(),
            self.get_latest_block().hash
        )
        
        block.mine_block(self.difficulty)
        self.chain.append(block)
        self.pending_transactions = []

    def is_chain_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            if current_block.hash != current_block.calculate_hash():
                return False
            if current_block.previous_hash != previous_block.hash:
                return False
        return True

    def get_irrigation_records(self, farmer_id: str = None) -> List[Dict]:
        records = []
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("type") == "irrigation":
                    if farmer_id is None or tx.get("farmer_id") == farmer_id:
                        record = tx.copy()
                        record["block_index"] = block.index
                        record["block_hash"] = block.hash
                        record["timestamp_readable"] = datetime.fromtimestamp(
                            tx.get("timestamp", 0)
                        ).strftime("%Y-%m-%d %H:%M:%S")
                        records.append(record)
        return records

    def get_soil_history(self, farmer_id: str = None) -> List[Dict]:
        history = []
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("type") in ["irrigation", "sensor_reading"]:
                    if farmer_id is None or tx.get("farmer_id") == farmer_id:
                        history.append({
                            "timestamp": tx.get("timestamp", 0),
                            "soil_moisture": tx.get("soil_moisture"),
                            "water_usage": tx.get("water_usage"),
                            "status": tx.get("status")
                        })
        return sorted(history, key=lambda x: x["timestamp"])

class SmartContract:
    def _init_(self, blockchain: AgriBlockchain):
        self.blockchain = blockchain
        self.thresholds = {
            "low_moisture": 30,
            "high_moisture": 70,
            "optimal_low": 45,
            "optimal_high": 65
        }

    def evaluate_irrigation(self, soil_moisture: float, farmer_id: str) -> Dict:
        status = ""
        action = ""
        
        if soil_moisture < self.thresholds["low_moisture"]:
            status = "CRITICAL - Irrigation Required"
            action = "START_IRRIGATION"
        elif soil_moisture < self.thresholds["optimal_low"]:
            status = "LOW - Irrigation Recommended"
            action = "START_IRRIGATION"
        elif soil_moisture <= self.thresholds["optimal_high"]:
            status = "OPTIMAL - No Action Needed"
            action = "MAINTAIN"
        elif soil_moisture < self.thresholds["high_moisture"]:
            status = "HIGH - Monitor Closely"
            action = "STOP_IRRIGATION"
        else:
            status = "EXCESSIVE - Stop Irrigation"
            action = "STOP_IRRIGATION"

        transaction = {
            "type": "irrigation_decision",
            "farmer_id": farmer_id,
            "soil_moisture": soil_moisture,
            "status": status,
            "action": action,
            "timestamp": time.time()
        }
        self.blockchain.add_transaction(transaction)
        
        return {
            "status": status,
            "action": action,
            "recommendation": f"Soil moisture is {soil_moisture}%. {status}",
            "thresholds": self.thresholds
        }

    def record_irrigation(self, farmer_id: str, soil_moisture: float, 
                         water_usage: float, action_taken: str) -> Dict:
        transaction = {
            "type": "irrigation",
            "farmer_id": farmer_id,
            "soil_moisture": round(soil_moisture, 2),
            "water_usage": round(water_usage, 2),
            "action_taken": action_taken,
            "status": "COMPLETED"
        }
        block_index = self.blockchain.add_transaction(transaction)
        return {
            "transaction_id": f"TX_{int(time.time())}",
            "block_index": block_index,
            "verified": True,
            "transaction": transaction
        }