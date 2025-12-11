#!/usr/bin/env python3
"""
Enhanced Supabase Connection and Table Debug Script
This script provides detailed debugging to identify the exact issue with Supabase
"""
import os
import sys
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
def load_env():
    """Load environment variables from .env file"""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print(f"📄 Loading environment from: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        print("✅ Environment variables loaded from .env file")
    else:
        print(f"⚠️ No .env file found at: {env_file}")

def print_section(title):
    """Print a clearly marked section"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_step(step_num, description):
    """Print a numbered step"""
    print(f"\n🔍 Step {step_num}: {description}")

def print_success(message):
    """Print success message"""
    print(f"✅ {message}")

def print_error(message):
    """Print error message"""
    print(f"❌ {message}")

def print_info(message):
    """Print info message"""
    print(f"💡 {message}")

def main():
    """Run detailed Supabase diagnostics"""
    print_section("SUPABASE DEBUG - DETAILED DIAGNOSTICS")
    print(f"🕐 Started at: {datetime.now()}")
    
    # Load environment variables
    load_env()
    
    # Step 1: Environment Variable Check
    print_step(1, "Checking Environment Variables")
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    print(f"   SUPABASE_URL: {'✅ Set' if supabase_url else '❌ Missing'}")
    if supabase_url:
        print(f"     URL Preview: {supabase_url[:30]}...{supabase_url[-10:]}")
        print(f"     URL Length: {len(supabase_url)} chars")
        print(f"     URL Starts with https: {supabase_url.startswith('https://')}")
        print(f"     URL Contains supabase.co: {'supabase.co' in supabase_url}")
    
    print(f"   SUPABASE_SERVICE_KEY: {'✅ Set' if supabase_key else '❌ Missing'}")
    if supabase_key:
        print(f"     Key Preview: {'***' + supabase_key[-10:]}")
        print(f"     Key Length: {len(supabase_key)} chars")
        print(f"     Key Format Check: {supabase_key.startswith('eyJ') or supabase_key.startswith('sb-')}")
    
    if not supabase_url or not supabase_key:
        print_error("Environment variables missing - cannot proceed")
        return False
    
    # Step 2: Import Test
    print_step(2, "Testing Supabase Import")
    try:
        from supabase import create_client
        print_success("Supabase library imported successfully")
        
        # Check version if available
        try:
            import supabase
            version = getattr(supabase, '__version__', 'unknown')
            print(f"💡 Supabase version: {version}")
        except:
            print("💡 Could not determine supabase version")
            
    except ImportError as e:
        print_error(f"Supabase import failed: {e}")
        print_info("Install with: pip install supabase")
        return False
    except Exception as e:
        print_error(f"Unexpected import error: {e}")
        return False
    
    # Step 3: Client Creation
    print_step(3, "Creating Supabase Client")
    try:
        print("   Creating client with provided credentials...")
        client = create_client(supabase_url, supabase_key)
        print_success("Supabase client created successfully")
        print(f"   Client type: {type(client)}")
        print(f"   Client attributes: {[attr for attr in dir(client) if not attr.startswith('_')][:10]}...")
    except TypeError as e:
        print_error(f"Client creation failed - Type Error: {e}")
        print_info("This might be a version compatibility issue")
        print_info("Try: pip install --upgrade supabase")
        return False
    except Exception as e:
        print_error(f"Client creation failed: {e}")
        print_info(f"Error type: {type(e).__name__}")
        return False
    
    # Step 4: Basic Connection Test
    print_step(4, "Testing Basic Database Connection")
    try:
        print("   Attempting to list tables...")
        # Try a generic query to test connection
        result = client.rpc('version').execute()
        print_success("Basic database connection successful")
        print(f"   Connection result type: {type(result)}")
        print(f"   Connection result has data: {hasattr(result, 'data')}")
    except Exception as e:
        print_error(f"Basic connection test failed: {e}")
        print_info(f"Error type: {type(e).__name__}")
        print_info("This might indicate network, auth, or service issues")
        # Continue to table tests anyway
    
    # Step 5: Table Existence Check
    print_step(5, "Checking elevenlabs_voices Table")
    try:
        print("   5a: Getting table reference...")
        table_ref = client.table("elevenlabs_voices")
        print_success("Table reference created")
        
        print("   5b: Building simple select query...")
        query = table_ref.select("*")
        print_success("Select query built")
        
        print("   5c: Adding limit...")
        query = query.limit(1)
        print_success("Limit added")
        
        print("   5d: Executing query...")
        result = query.execute()
        print_success("Query executed successfully")
        
        print("   5e: Analyzing result...")
        print(f"      Result type: {type(result)}")
        print(f"      Result has data attr: {hasattr(result, 'data')}")
        
        if hasattr(result, 'data'):
            data = result.data
            print(f"      Data type: {type(data)}")
            print(f"      Data length: {len(data) if data else 0}")
            
            if data and len(data) > 0:
                print_success(f"Table exists and has {len(data)} records")
                print(f"      Sample record keys: {list(data[0].keys())}")
            else:
                print_success("Table exists but is empty")
        else:
            print_error("Result missing 'data' attribute")
            print(f"      Result attributes: {dir(result)}")
        
    except Exception as e:
        error_str = str(e).lower()
        print_error(f"Table check failed: {e}")
        print_info(f"Error type: {type(e).__name__}")
        
        if "relation \"elevenlabs_voices\" does not exist" in error_str:
            print_info("❗ TABLE MISSING - Need to run migration")
            print_info("🔧 Solution: Run backend/migrations/create_elevenlabs_voices_table.sql")
        elif "permission" in error_str or "denied" in error_str:
            print_info("❗ PERMISSION ISSUE - Service key might be wrong")
            print_info("🔧 Solution: Check SUPABASE_SERVICE_KEY in .env file")
        elif "column" in error_str:
            print_info("❗ COLUMN ISSUE - Table schema might be wrong")
            print_info("🔧 Solution: Check table schema matches migration")
        else:
            print_info("❗ UNKNOWN TABLE ERROR")
            print_info("🔧 Solution: Check Supabase dashboard for table status")
    
    # Step 6: Schema Information (if table exists)
    print_step(6, "Getting Table Schema Information")
    try:
        # Try to get table information
        schema_result = client.rpc('get_table_info', {'table_name': 'elevenlabs_voices'}).execute()
        if schema_result.data:
            print_success("Schema information retrieved")
            print(f"   Schema data: {schema_result.data}")
        else:
            print_info("No schema information available")
    except Exception as e:
        print_info(f"Schema check not available: {e}")
    
    # Step 7: Test Insert (if table exists)
    print_step(7, "Testing Insert Operation")
    try:
        print("   Attempting test insert...")
        test_data = {
            "voice_id": "test_debug_voice_001",
            "name": "Debug Test Voice",
            "description": "Test voice for debugging",
            "category": "test",
            "labels": ["debug", "test"],
            "preview_url": None,
            "gender": None,
            "age": None,
            "accent": None,
            "use_case": None,
            "is_active": True
        }
        
        insert_result = client.table("elevenlabs_voices").insert(test_data).execute()
        
        if insert_result.data:
            print_success("Test insert successful")
            print(f"   Inserted records: {len(insert_result.data)}")
            
            # Clean up test data
            print("   Cleaning up test data...")
            delete_result = client.table("elevenlabs_voices")\
                .delete()\
                .eq("voice_id", "test_debug_voice_001")\
                .execute()
            print_success("Test data cleaned up")
        else:
            print_error("Insert returned no data")
            
    except Exception as e:
        print_error(f"Insert test failed: {e}")
        error_str = str(e).lower()
        if "duplicate" in error_str or "unique" in error_str:
            print_info("❗ DUPLICATE KEY - This is expected if test data exists")
        elif "column" in error_str:
            print_info("❗ COLUMN MISMATCH - Schema might be different")
        else:
            print_info("❗ INSERT ERROR - Check table permissions/structure")
    
    print_section("DIAGNOSTIC SUMMARY")
    print_success("Diagnostic complete - check output above for specific issues")
    print(f"🕐 Completed at: {datetime.now()}")
    
    return True

if __name__ == "__main__":
    main()
