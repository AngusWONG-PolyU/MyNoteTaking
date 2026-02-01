from flask import Blueprint, jsonify, request
from src.models.note import Note, db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

note_bp = Blueprint('note', __name__)

def parse_time_string(time_str):
    """
    Parse a time string with support for multiple formats.
    Supports: HH:MM, HH:MM:SS, HH:MM:SS.ffffff (fractional seconds)
    Returns a time object or None if parsing fails.
    """
    if not time_str:
        return None
    
    # List of time formats to try, in order of specificity
    time_formats = [
        '%H:%M:%S.%f',  # HH:MM:SS.ffffff (with fractional seconds - up to microseconds)
        '%H:%M:%S',     # HH:MM:SS
        '%H:%M',        # HH:MM
    ]
    
    for fmt in time_formats:
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    
    # If all formats fail, log a warning and return None
    logger.warning(f"Failed to parse time string: '{time_str}'. Supported formats: HH:MM, HH:MM:SS, HH:MM:SS.ffffff")
    return None

@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400
        
        note = Note(title=data['title'], content=data['content'])
        
        # Add new fields
        if 'location' in data:
            note.location = data['location']
        if 'tags' in data:
            note.tags = data['tags']
        if 'event_date' in data and data['event_date']:
            try:
                note.event_date = datetime.strptime(data['event_date'], '%Y-%m-%d').date()
            except ValueError:
                pass
        if 'event_time' in data and data['event_time']:
            parsed_time = parse_time_string(data['event_time'])
            if parsed_time is not None:
                note.event_time = parsed_time
                
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)
        
        if 'location' in data:
            note.location = data['location']
        if 'tags' in data:
            note.tags = data['tags']
        if 'event_date' in data:
            if data['event_date']:
                try:
                    note.event_date = datetime.strptime(data['event_date'], '%Y-%m-%d').date()
                except ValueError:
                    pass
            else:
                note.event_date = None
        if 'event_time' in data:
            if data['event_time']:
                parsed_time = parse_time_string(data['event_time'])
                if parsed_time is not None:
                    note.event_time = parsed_time
            else:
                note.event_time = None
        
        db.session.commit()
        return jsonify(note.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.updated_at.desc()).all()
    
    return jsonify([note.to_dict() for note in notes])

