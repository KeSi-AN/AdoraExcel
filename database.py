from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from contextlib import contextmanager
import os
from dotenv import load_dotenv
from models import Base, ExcelFile, ExcelTable
from typing import Generator, Optional, Dict, Any, List, Tuple
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables
load_dotenv()

# PostgreSQL Configuration
POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'Sweethome%40143')
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB', 'Adora_AI')
DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db_session() -> Generator[scoped_session, None, None]:
    """Database session context manager."""
    session = scoped_session(SessionLocal)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def init_db():
    """Initialize the database tables."""
    Base.metadata.create_all(bind=engine)

def is_duplicate_file(file_hash: str) -> bool:
    """Check if a file with the given hash already exists in the database."""
    with get_db_session() as db_session:
        existing_file = db_session.query(ExcelFile).filter(ExcelFile.file_hash == file_hash).first()
        return existing_file is not None

def save_excel_file(file_name: str, file_path: str, file_hash: str, tables_data: Dict[str, Any]) -> Optional[int]:
    """Save Excel file and its tables to the database."""
    with get_db_session() as db_session:
        try:
            # Create ExcelFile record
            excel_file = ExcelFile(
                file_name=file_name,
                file_path=file_path,
                file_hash=file_hash
            )
            db_session.add(excel_file)
            db_session.flush()
            
            # Prepare and add ExcelTable records
            for sheet_name, tables in tables_data.items():
                for table_name, table_data in tables.items():
                    excel_table = ExcelTable(
                        excel_file_id=excel_file.id,
                        sheet_name=sheet_name,
                        table_name=table_name,
                        data=table_data  # Data will be serialized by SQLAlchemy
                    )
                    db_session.add(excel_table)
            
            db_session.commit()
            return excel_file.id
            
        except SQLAlchemyError as e:
            db_session.rollback()
            raise Exception(f"Failed to save Excel file to database: {str(e)}")

def get_excel_file(file_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve an Excel file and its tables by ID."""
    with get_db_session() as db_session:
        file = db_session.query(ExcelFile).filter_by(id=file_id).first()
        if not file:
            return None
            
        tables_by_sheet = {}
        for table in file.tables:
            tables_by_sheet.setdefault(table.sheet_name, {})[table.table_name] = table.data
            
        return {
            'id': file.id,
            'file_name': file.file_name,
            'file_path': file.file_path,
            'uploaded_at': file.uploaded_at,  # Keep as datetime object
            'tables': tables_by_sheet
        }

def list_excel_files() -> List[Dict[str, Any]]:
    """List all Excel files in the database."""
    with get_db_session() as db_session:
        files = db_session.query(ExcelFile).order_by(ExcelFile.uploaded_at.desc()).all()
        return [{
            'id': f.id,
            'file_name': f.file_name,
            'uploaded_at': f.uploaded_at,  # Keep as datetime object
            'tables_count': len(f.tables)
        } for f in files]

def duplicate_excel_file(file_id: int) -> tuple[bool, str, int]:
    """
    Create a duplicate of an existing Excel file with a new sequential number.
    
    Args:
        file_id: ID of the file to duplicate
        
    Returns:
        tuple: (success: bool, message: str, new_file_id: int)
    """
    with get_db_session() as db_session:
        try:
            # Get the file to duplicate
            original_file = db_session.query(ExcelFile).filter(ExcelFile.id == file_id).first()
            if not original_file:
                return False, "Original file not found", -1
            
            # Get the next available file number
            max_file_num = db_session.query(
                db.func.max(
                    db.cast(
                        db.func.regexp_replace(ExcelFile.file_name, r'^file(\d+).*', '\\1'),
                        db.Integer
                    )
                )
            ).scalar() or 0
            new_file_num = max_file_num + 1
            
            # Create new file name with next sequential number
            file_name_parts = os.path.splitext(original_file.file_name)
            new_file_name = f"file{new_file_num}{file_name_parts[1] if len(file_name_parts) > 1 else ''}"
            
            # Create new file path
            original_dir = os.path.dirname(original_file.file_path)
            new_file_path = os.path.join(original_dir, new_file_name)
            
            # Copy the file
            import shutil
            shutil.copy2(original_file.file_path, new_file_path)
            
            # Create new database record
            new_file = ExcelFile(
                file_name=new_file_name,
                file_path=new_file_path,
                file_hash=calculate_file_hash(open(new_file_path, 'rb').read())
            )
            db_session.add(new_file)
            db_session.flush()  # Get the new file ID
            
            # Duplicate all tables and their data
            original_tables = db_session.query(ExcelTable).filter(
                ExcelTable.excel_file_id == file_id
            ).all()
            
            for table in original_tables:
                new_table = ExcelTable(
                    excel_file_id=new_file.id,
                    sheet_name=table.sheet_name,
                    table_name=table.table_name,
                    data=table.data  # This should be a deep copy if it's a mutable object
                )
                db_session.add(new_table)
            
            db_session.commit()
            return True, f"File duplicated successfully as {new_file_name}", new_file.id
            
        except Exception as e:
            db_session.rollback()
            import traceback
            traceback.print_exc()
            return False, f"Error duplicating file: {str(e)}", -1


def delete_excel_file(file_id: int) -> tuple[bool, str]:
    """
    Delete an Excel file and its associated data from both database and file system.
    Then renumber remaining files to maintain sequential order.
    
    Args:
        file_id: ID of the file to delete
        
    Returns:
        tuple: (success: bool, message: str)
    """
    with get_db_session() as db_session:
        try:
            # Start a transaction
            file_to_delete = db_session.query(ExcelFile).filter(ExcelFile.id == file_id).first()
            if not file_to_delete:
                return False, "File not found"
                
            file_path = file_to_delete.file_path
            
            # Get all files ordered by ID to determine new numbering
            all_files = db_session.query(ExcelFile).order_by(ExcelFile.id).all()
            
            # Delete associated tables first (due to foreign key constraint)
            db_session.query(ExcelTable).filter(ExcelTable.excel_file_id == file_id).delete()
            
            # Delete the file record from database
            db_session.delete(file_to_delete)
            
            # If database deletion was successful, delete the actual file
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                    # Try to remove the directory if it's empty
                    directory = os.path.dirname(file_path)
                    if os.path.exists(directory) and not os.listdir(directory):
                        os.rmdir(directory)
                
                # Get remaining files after deletion
                remaining_files = db_session.query(ExcelFile).order_by(ExcelFile.id).all()
                
                # Update file names to maintain sequential numbering
                for index, file in enumerate(remaining_files, 1):
                    # Extract file extension
                    file_name = file.file_name
                    file_ext = os.path.splitext(file_name)[1] if '.' in file_name else ''
                    
                    # Create new file name with sequential number
                    new_name = f"file{index}{file_ext}"
                    
                    # If name is changing, update the database and rename the file
                    if file_name != new_name:
                        # Update database record
                        file.file_name = new_name
                        
                        # Update file path
                        old_path = file.file_path
                        new_path = os.path.join(os.path.dirname(old_path), new_name)
                        file.file_path = new_path
                        
                        # Rename the actual file
                        if os.path.exists(old_path):
                            os.rename(old_path, new_path)
                
                db_session.commit()
                return True, "File deleted and numbering updated successfully"
                
            except Exception as e:
                # If file operations fail, log the error but still return success for DB operation
                import logging
                logging.error(f"Error during file operations: {str(e)}")
                db_session.rollback()
                return False, f"Error during file operations: {str(e)}"
                
        except SQLAlchemyError as e:
            db_session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db_session.rollback()
            return False, f"Unexpected error: {str(e)}"
