const express = require('express');
const pool = require('../db');
const router = express.Router();

function shuffleArray(array) {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
}

router.get('/list', async (req, res) => {
  try {
    const result = await pool.query(`
      SELECT id, title, description, duration_minutes, total_questions
      FROM exams
      WHERE is_active = true
      ORDER BY created_at DESC
    `);
    res.json(result.rows);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: '获取考试列表失败' });
  }
});

router.get('/:id', async (req, res) => {
  const { id } = req.params;
  const { studentName } = req.query;
  
  try {
    const examResult = await pool.query(`
      SELECT id, title, description, duration_minutes, total_questions, randomize_questions
      FROM exams
      WHERE id = $1 AND is_active = true
    `, [id]);

    if (examResult.rows.length === 0) {
      return res.status(404).json({ error: '考试不存在' });
    }

    const exam = examResult.rows[0];
    const shouldRandomize = exam.randomize_questions !== false;

    let questionsQuery = `
      SELECT id, question_text, option_a, option_b, option_c, option_d
      FROM questions
      WHERE exam_id = $1
    `;
    
    if (shouldRandomize) {
      questionsQuery += ' ORDER BY RANDOM()';
    } else {
      questionsQuery += ' ORDER BY id';
    }

    const questionsResult = await pool.query(questionsQuery, [id]);
    let questions = questionsResult.rows;

    if (shouldRandomize && exam.total_questions > 0 && questions.length > exam.total_questions) {
      questions = shuffleArray(questions).slice(0, exam.total_questions);
    }

    const shuffledQuestions = questions.map(q => {
      const optionKeys = ['A', 'B', 'C', 'D'];
      const optionValues = [q.option_a, q.option_b, q.option_c, q.option_d];
      
      const options = {};
      optionKeys.forEach((key, index) => {
        options[key] = optionValues[index];
      });

      return {
        id: q.id,
        questionText: q.question_text,
        options
      };
    });

    exam.questions = shuffledQuestions;

    res.json(exam);
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: '获取考试详情失败' });
  }
});

router.post('/submit', async (req, res) => {
  const { examId, studentName, answers } = req.body;

  if (!examId || !studentName || !answers) {
    return res.status(400).json({ error: '缺少必要参数' });
  }

  const client = await pool.connect();

  try {
    await client.query('BEGIN');

    const existingResult = await client.query(`
      SELECT id FROM exam_results 
      WHERE exam_id = $1 AND student_name = $2
      FOR UPDATE
    `, [examId, studentName]);

    if (existingResult.rows.length > 0) {
      await client.query('ROLLBACK');
      return res.status(409).json({ 
        error: '考试已提交',
        resultId: existingResult.rows[0].id 
      });
    }

    const correctAnswersResult = await client.query(`
      SELECT id, correct_answer
      FROM questions
      WHERE exam_id = $1
    `, [examId]);

    if (correctAnswersResult.rows.length === 0) {
      await client.query('ROLLBACK');
      return res.status(404).json({ error: '考试不存在' });
    }

    const correctAnswers = correctAnswersResult.rows.reduce((acc, q) => {
      acc[q.id] = q.correct_answer;
      return acc;
    }, {});

    const totalQuestions = Object.keys(correctAnswers).length;
    let correctCount = 0;

    for (const [questionId, userAnswer] of Object.entries(answers)) {
      if (correctAnswers[questionId] && userAnswer === correctAnswers[questionId]) {
        correctCount++;
      }
    }

    const score = totalQuestions > 0 ? Math.round((correctCount / totalQuestions) * 100) : 0;
    const passed = score >= 60;

    const resultResult = await client.query(`
      INSERT INTO exam_results (exam_id, student_name, score, passed, total_questions, correct_answers)
      VALUES ($1, $2, $3, $4, $5, $6)
      RETURNING id
    `, [examId, studentName, score, passed, totalQuestions, correctCount]);

    const resultId = resultResult.rows[0].id;

    const insertValues = [];
    for (const [questionId, userAnswer] of Object.entries(answers)) {
      if (correctAnswers[questionId]) {
        insertValues.push([
          resultId,
          questionId,
          userAnswer,
          userAnswer === correctAnswers[questionId],
        ]);
      }
    }

    if (insertValues.length > 0) {
      const placeholders = insertValues.map((_, i) => 
        `($${i * 4 + 1}, $${i * 4 + 2}, $${i * 4 + 3}, $${i * 4 + 4})`
      ).join(', ');
      
      const flatValues = insertValues.flat();
      await client.query(`
        INSERT INTO user_answers (result_id, question_id, user_answer, is_correct)
        VALUES ${placeholders}
      `, flatValues);
    }

    await client.query('COMMIT');

    res.json({
      resultId,
      score,
      correctCount,
      totalQuestions,
      passed,
    });
  } catch (err) {
    await client.query('ROLLBACK');
    console.error(err);
    
    if (err.code === '23505') {
      return res.status(409).json({ error: '考试已提交' });
    }
    
    res.status(500).json({ error: '提交考试失败' });
  } finally {
    client.release();
  }
});

router.get('/result/:resultId', async (req, res) => {
  const { resultId } = req.params;
  try {
    const result = await pool.query(`
      SELECT er.*, e.title as exam_title
      FROM exam_results er
      JOIN exams e ON er.exam_id = e.id
      WHERE er.id = $1
    `, [resultId]);

    if (result.rows.length === 0) {
      return res.status(404).json({ error: '结果不存在' });
    }

    const answers = await pool.query(`
      SELECT 
        q.question_text,
        ua.user_answer,
        q.correct_answer,
        ua.is_correct,
        q.option_a, q.option_b, q.option_c, q.option_d
      FROM user_answers ua
      JOIN questions q ON ua.question_id = q.id
      WHERE ua.result_id = $1
    `, [resultId]);

    res.json({
      ...result.rows[0],
      answers: answers.rows.map(a => ({
        questionText: a.question_text,
        userAnswer: a.user_answer,
        correctAnswer: a.correct_answer,
        isCorrect: a.is_correct,
        options: {
          A: a.option_a,
          B: a.option_b,
          C: a.option_c,
          D: a.option_d,
        },
      })),
    });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: '获取考试结果失败' });
  }
});

module.exports = router;
