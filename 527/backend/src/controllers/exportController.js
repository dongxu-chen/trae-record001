const Annotation = require('../models/Annotation');
const Document = require('../models/Document');

exports.exportJSON = async (req, res) => {
  try {
    const { taskId } = req.params;
    const { format = 'flat' } = req.query;
    
    const annotations = await Annotation.find({ taskId })
      .populate('documentId', 'text meta status');
    
    if (format === 'nested') {
      const exportData = annotations.map(ann => ({
        id: ann._id.toString(),
        documentId: ann.documentId._id.toString(),
        text: ann.documentId.text,
        meta_source: ann.documentId.meta?.source || '',
        meta_timestamp: ann.documentId.meta?.timestamp || null,
        meta_author: ann.documentId.meta?.author || '',
        document_status: ann.documentId.status,
        entity_count: ann.entities.length,
        relation_count: ann.relations.length,
        event_count: ann.events.length,
        entities: ann.entities.map(e => ({
          id: e.id,
          start: e.start,
          end: e.end,
          text: e.text,
          label: e.label,
          isPreAnnotated: e.isPreAnnotated
        })),
        relations: ann.relations.map(r => ({
          id: r.id,
          sourceId: r.sourceId,
          targetId: r.targetId,
          label: r.label,
          isPreAnnotated: r.isPreAnnotated
        })),
        events: ann.events.map(e => ({
          id: e.id,
          triggerStart: e.triggerStart,
          triggerEnd: e.triggerEnd,
          triggerText: e.triggerText,
          label: e.label,
          arguments: e.arguments,
          isPreAnnotated: e.isPreAnnotated
        })),
        annotatedAt: ann.updatedAt,
        annotator: ann.annotator
      }));
      
      res.setHeader('Content-Type', 'application/json');
      res.setHeader('Content-Disposition', `attachment; filename="annotations_${taskId}_nested.json"`);
      return res.json(exportData);
    }
    
    const flatEntities = [];
    const flatRelations = [];
    const flatEvents = [];
    const flatDocuments = [];
    
    annotations.forEach(ann => {
      const docId = ann.documentId._id.toString();
      
      flatDocuments.push({
        document_id: docId,
        document_text: ann.documentId.text,
        document_status: ann.documentId.status,
        document_meta_source: ann.documentId.meta?.source || '',
        document_meta_timestamp: ann.documentId.meta?.timestamp || null,
        document_meta_author: ann.documentId.meta?.author || '',
        annotated_at: ann.updatedAt,
        annotator: ann.annotator || '',
        entity_count: ann.entities.length,
        relation_count: ann.relations.length,
        event_count: ann.events.length,
        task_id: taskId
      });
      
      ann.entities.forEach(e => {
        flatEntities.push({
          entity_id: e.id,
          entity_text: e.text,
          entity_label: e.label,
          entity_start: e.start,
          entity_end: e.end,
          entity_is_preannotated: e.isPreAnnotated || false,
          entity_confidence: e.confidence || null,
          document_id: docId,
          task_id: taskId
        });
      });
      
      ann.relations.forEach(r => {
        const sourceEntity = ann.entities.find(e => e.id === r.sourceId);
        const targetEntity = ann.entities.find(e => e.id === r.targetId);
        
        flatRelations.push({
          relation_id: r.id,
          relation_label: r.label,
          relation_source_id: r.sourceId,
          relation_source_text: sourceEntity?.text || '',
          relation_source_label: sourceEntity?.label || '',
          relation_target_id: r.targetId,
          relation_target_text: targetEntity?.text || '',
          relation_target_label: targetEntity?.label || '',
          relation_is_preannotated: r.isPreAnnotated || false,
          document_id: docId,
          task_id: taskId
        });
      });
      
      ann.events.forEach(e => {
        flatEvents.push({
          event_id: e.id,
          event_label: e.label,
          event_trigger_start: e.triggerStart,
          event_trigger_end: e.triggerEnd,
          event_trigger_text: e.triggerText,
          event_arguments_count: e.arguments?.length || 0,
          event_is_preannotated: e.isPreAnnotated || false,
          document_id: docId,
          task_id: taskId
        });
      });
    });
    
    const flatExport = {
      metadata: {
        task_id: taskId,
        export_at: new Date(),
        format: 'flat',
        document_count: flatDocuments.length,
        entity_count: flatEntities.length,
        relation_count: flatRelations.length,
        event_count: flatEvents.length
      },
      documents: flatDocuments,
      entities: flatEntities,
      relations: flatRelations,
      events: flatEvents
    };
    
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="annotations_${taskId}_flat.json"`);
    res.json(flatExport);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.exportCoNLL = async (req, res) => {
  try {
    const { taskId } = req.params;
    
    const annotations = await Annotation.find({ taskId })
      .populate('documentId', 'text');
    
    let conllOutput = '';
    
    annotations.forEach((ann, docIdx) => {
      const text = ann.documentId.text;
      const words = text.split(/\s+/);
      
      let charIndex = 0;
      const wordEntities = [];
      
      words.forEach((word, wordIdx) => {
        const wordStart = text.indexOf(word, charIndex);
        const wordEnd = wordStart + word.length;
        
        let entityLabel = 'O';
        ann.entities.forEach(entity => {
          if (wordStart >= entity.start && wordEnd <= entity.end) {
            if (wordStart === entity.start) {
              entityLabel = `B-${entity.label}`;
            } else {
              entityLabel = `I-${entity.label}`;
            }
          }
        });
        
        wordEntities.push({ word, entityLabel });
        charIndex = wordEnd;
      });
      
      conllOutput += `-DOCSTART- -X- -X- O\n\n`;
      wordEntities.forEach(item => {
        conllOutput += `${item.word} -X- -X- ${item.entityLabel}\n`;
      });
      conllOutput += '\n';
    });
    
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="annotations_${taskId}.conll"`);
    res.send(conllOutput);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

exports.getStats = async (req, res) => {
  try {
    const { taskId } = req.params;
    
    const totalDocs = await Document.countDocuments({ taskId });
    const annotatedDocs = await Document.countDocuments({ taskId, status: 'annotated' });
    const reviewedDocs = await Document.countDocuments({ taskId, status: 'reviewed' });
    
    const annotations = await Annotation.find({ taskId });
    
    const entityCounts = {};
    const relationCounts = {};
    const eventCounts = {};
    
    annotations.forEach(ann => {
      ann.entities.forEach(e => {
        entityCounts[e.label] = (entityCounts[e.label] || 0) + 1;
      });
      ann.relations.forEach(r => {
        relationCounts[r.label] = (relationCounts[r.label] || 0) + 1;
      });
      ann.events.forEach(e => {
        eventCounts[e.label] = (eventCounts[e.label] || 0) + 1;
      });
    });
    
    res.json({
      total: totalDocs,
      annotated: annotatedDocs,
      reviewed: reviewedDocs,
      pending: totalDocs - annotatedDocs - reviewedDocs,
      entityCounts,
      relationCounts,
      eventCounts
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
