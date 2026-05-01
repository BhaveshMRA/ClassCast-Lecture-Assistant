import asyncio
import logging
from fastapi import APIRouter, File, UploadFile, HTTPException, BackgroundTasks

from app.utils.slides import extract_slides_text
from app.pipeline.graph import process_slide_batch
from app.broadcaster import broadcaster
from app.course_state import course_state

logger = logging.getLogger(__name__)

router = APIRouter()


async def process_slides_background(slides: list[str]):
    """Process each slide with a slight delay so students don't get flooded."""
    for i, text in enumerate(slides, start=1):
        try:
            await process_slide_batch(text, i)
            # Add a short delay between slides so events arrive distinctly
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Background slide processing failed on slide {i}: {e}")


@router.post("/ingest/slides")
async def upload_slides(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Ingest a PPTX or PDF file.
    Extracts text per slide/page and feeds it into the pipeline directly,
    bypassing Whisper and the audio batch accumulator.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    filename = file.filename.lower()
    if not filename.endswith((".pptx", ".pdf")):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file type. Please upload .pptx or .pdf"
        )
        
    try:
        content = await file.read()
        slides = extract_slides_text(content, filename)
    except Exception as e:
        logger.error(f"Failed to extract slides: {e}")
        raise HTTPException(status_code=400, detail=f"Extraction failed: {str(e)}")
        
    if not slides:
        return {"status": "ok", "message": "No text could be extracted from the slides.", "slide_count": 0}
        
    # Notify clients that slides are being processed
    await broadcaster.publish("audit", {
        "concept": f"Processing {len(slides)} slides",
        "concept_type": "ADMIN",
        "action": "SKIP",
        "reason": f"Uploaded {filename}"
    })
        
    background_tasks.add_task(process_slides_background, slides)
    
    return {
        "status": "ok",
        "message": f"Processing {len(slides)} slides in the background.",
        "slide_count": len(slides)
    }

@router.post("/ingest/syllabus")
async def upload_syllabus(file: UploadFile = File(...)):
    """
    Ingest a PPTX, PDF, or TXT file as the course syllabus/notes.
    Extracts all text and stores it in the global course_state for RAG injection.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
        
    filename = file.filename.lower()
    if not filename.endswith((".pptx", ".pdf", ".txt")):
        raise HTTPException(
            status_code=400, 
            detail="Unsupported file type. Please upload .pptx, .pdf, or .txt"
        )
        
    try:
        content = await file.read()
        if filename.endswith(".txt"):
            text = content.decode("utf-8")
        else:
            slides = extract_slides_text(content, filename)
            text = "\n\n".join(slides)
    except Exception as e:
        logger.error(f"Failed to extract syllabus: {e}")
        raise HTTPException(status_code=400, detail=f"Extraction failed: {str(e)}")
        
    if not text.strip():
        return {"status": "ok", "message": "No text could be extracted.", "length": 0}
        
    course_state.set_syllabus(text)
    
    # Notify clients that syllabus is active
    await broadcaster.publish("audit", {
        "concept": f"Syllabus Loaded",
        "concept_type": "ADMIN",
        "action": "STORE",
        "reason": f"Uploaded {filename} ({len(text)} chars)"
    })
    
    return {
        "status": "ok",
        "message": "Syllabus loaded successfully.",
        "length": len(text)
    }
