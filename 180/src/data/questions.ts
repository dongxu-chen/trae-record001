import { Question, KnowledgePoint } from '../types'

export const knowledgePoints: KnowledgePoint[] = [
  { id: 'react-basic', name: 'React基础', category: '前端框架' },
  { id: 'react-hook', name: 'React Hooks', category: '前端框架' },
  { id: 'js-basic', name: 'JavaScript基础', category: '编程语言' },
  { id: 'js-es6', name: 'ES6特性', category: '编程语言' },
  { id: 'css-basic', name: 'CSS基础', category: '样式' },
  { id: 'css-layout', name: 'CSS布局', category: '样式' },
  { id: 'html-basic', name: 'HTML基础', category: '标记语言' },
  { id: 'http-basic', name: 'HTTP协议', category: '网络' },
  { id: 'typescript', name: 'TypeScript', category: '编程语言' },
  { id: 'git-basic', name: 'Git基础', category: '版本控制' }
]

export const questionBank: Question[] = [
  {
    id: 1,
    type: 'single',
    title: 'React是由哪家公司开发的？',
    options: ['Google', 'Facebook (Meta)', 'Microsoft', 'Amazon'],
    answer: 1,
    score: 10,
    analysis: 'React是由Facebook（现Meta）于2013年开源的前端框架。',
    knowledgePoints: ['react-basic']
  },
  {
    id: 2,
    type: 'single',
    title: '以下哪个不是JavaScript的数据类型？',
    options: ['string', 'boolean', 'float', 'undefined'],
    answer: 2,
    score: 10,
    analysis: 'JavaScript中没有单独的float类型，浮点数使用number类型表示。',
    knowledgePoints: ['js-basic']
  },
  {
    id: 3,
    type: 'multiple',
    title: '以下哪些是React的Hook？（多选）',
    options: ['useState', 'useEffect', 'useComponent', 'useCallback'],
    answer: [0, 1, 3],
    score: 15,
    analysis: 'useState、useEffect、useCallback都是React官方提供的Hook，useComponent不是。',
    knowledgePoints: ['react-hook']
  },
  {
    id: 4,
    type: 'multiple',
    title: '以下哪些是有效的CSS选择器？（多选）',
    options: ['.class-name', '#id', '::before', '$variable'],
    answer: [0, 1, 2],
    score: 15,
    analysis: '.class-name是类选择器，#id是ID选择器，::before是伪元素选择器，$variable是Sass变量语法不是CSS选择器。',
    knowledgePoints: ['css-basic']
  },
  {
    id: 5,
    type: 'judge',
    title: 'TypeScript是JavaScript的超集。',
    options: ['正确', '错误'],
    answer: true,
    score: 10,
    analysis: 'TypeScript是JavaScript的超集，它在JavaScript的基础上添加了静态类型系统。',
    knowledgePoints: ['typescript']
  },
  {
    id: 6,
    type: 'judge',
    title: 'HTML中的<div>标签是行内元素。',
    options: ['正确', '错误'],
    answer: false,
    score: 10,
    analysis: '<div>是块级元素，不是行内元素。行内元素如<span>、<a>等。',
    knowledgePoints: ['html-basic']
  },
  {
    id: 7,
    type: 'single',
    title: 'HTTP状态码404表示什么？',
    options: ['服务器错误', '页面未找到', '请求成功', '重定向'],
    answer: 1,
    score: 10,
    analysis: '404 Not Found表示请求的资源在服务器上不存在。',
    knowledgePoints: ['http-basic']
  },
  {
    id: 8,
    type: 'single',
    title: 'Git中用于查看提交历史的命令是？',
    options: ['git status', 'git log', 'git diff', 'git show'],
    answer: 1,
    score: 10,
    analysis: 'git log用于查看提交历史记录，git status查看工作区状态，git diff查看差异。',
    knowledgePoints: ['git-basic']
  },
  {
    id: 9,
    type: 'multiple',
    title: '以下哪些是ES6新增的特性？（多选）',
    options: ['let/const', '箭头函数', 'Promise', 'var关键字'],
    answer: [0, 1, 2],
    score: 10,
    analysis: 'let/const、箭头函数、Promise都是ES6新增特性，var在ES6之前就存在。',
    knowledgePoints: ['js-es6']
  },
  {
    id: 10,
    type: 'judge',
    title: 'CSS中的flex布局可以实现垂直居中。',
    options: ['正确', '错误'],
    answer: true,
    score: 10,
    analysis: '使用display: flex配合align-items: center和justify-content: center可以轻松实现垂直水平居中。',
    knowledgePoints: ['css-layout']
  },
  {
    id: 11,
    type: 'single',
    title: 'React组件的生命周期方法componentDidMount在什么时候调用？',
    options: ['组件渲染前', '组件第一次渲染后', '组件更新后', '组件卸载前'],
    answer: 1,
    score: 10,
    analysis: 'componentDidMount在组件第一次渲染到DOM后调用，常用于数据获取和DOM操作。',
    knowledgePoints: ['react-basic']
  },
  {
    id: 12,
    type: 'single',
    title: '以下哪个不是JavaScript的基本数据类型？',
    options: ['number', 'string', 'array', 'boolean'],
    answer: 2,
    score: 10,
    analysis: 'array是引用类型，不是基本数据类型。JavaScript的基本数据类型包括：number、string、boolean、null、undefined、symbol、bigint。',
    knowledgePoints: ['js-basic']
  },
  {
    id: 13,
    type: 'multiple',
    title: '以下哪些是React中的状态管理方案？（多选）',
    options: ['Redux', 'MobX', 'Vuex', 'Context API'],
    answer: [0, 1, 3],
    score: 15,
    analysis: 'Redux、MobX、React的Context API都是React常用的状态管理方案，Vuex是Vue的状态管理方案。',
    knowledgePoints: ['react-basic']
  },
  {
    id: 14,
    type: 'judge',
    title: 'CSS中position: fixed相对于视口定位。',
    options: ['正确', '错误'],
    answer: true,
    score: 10,
    analysis: 'position: fixed相对于浏览器视口定位，元素会固定在屏幕上，不随滚动条移动。',
    knowledgePoints: ['css-layout']
  },
  {
    id: 15,
    type: 'single',
    title: 'HTTP请求方法中，哪个用于提交数据创建资源？',
    options: ['GET', 'POST', 'PUT', 'DELETE'],
    answer: 1,
    score: 10,
    analysis: 'POST方法用于提交数据创建新资源，GET用于获取，PUT用于更新，DELETE用于删除。',
    knowledgePoints: ['http-basic']
  }
]

export const EXAM_DURATION = 600

export function getRandomQuestions(count: number = 10): Question[] {
  const shuffled = [...questionBank].sort(() => Math.random() - 0.5)
  return shuffled.slice(0, Math.min(count, questionBank.length))
}

export const mockQuestions = questionBank.slice(0, 10)
