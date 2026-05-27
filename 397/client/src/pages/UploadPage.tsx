import React, { useState } from 'react';
import { Form, Input, Select, InputNumber, Upload, Button, Card, message, Alert } from 'antd';
import { UploadOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { templateAPI } from '../services/api';
import { CATEGORIES, COMPLEXITY } from '../utils/constants';

const { TextArea } = Input;
const { Option } = Select;

const UploadPage: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [thumbnailFile, setThumbnailFile] = useState<File | null>(null);
  const [previewFiles, setPreviewFiles] = useState<File[]>([]);
  const [templateFile, setTemplateFile] = useState<File | null>(null);

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      const formData = new FormData();
      
      Object.keys(values).forEach(key => {
        if (key === 'tags') {
          values[key].forEach((tag: string) => formData.append('tags[]', tag));
        } else {
          formData.append(key, values[key]);
        }
      });

      if (thumbnailFile) {
        formData.append('thumbnail', thumbnailFile);
      }
      
      previewFiles.forEach(file => {
        formData.append('previewImages', file);
      });
      
      if (templateFile) {
        formData.append('file', templateFile);
      }

      await templateAPI.createTemplate(formData);
      message.success('模板上传成功');
      navigate('/profile?tab=templates');
    } catch (error: any) {
      message.error(error.response?.data?.message || '上传失败');
    } finally {
      setLoading(false);
    }
  };

  const normFile = (e: any) => {
    if (Array.isArray(e)) return e;
    return e?.fileList;
  };

  return (
    <div className="max-w-4xl mx-auto">
      <Card title="上传新模板" style={{ background: '#1E293B', borderRadius: '16px' }}>
        <Alert
          message="模板审核说明"
          description={
            <ul className="list-disc list-inside mt-2 space-y-1 text-sm">
              <li>提交后模板将进入审核状态，审核通过后上架展示</li>
              <li>审核时间通常为1-3个工作日</li>
              <li>审核通过后将通过站内信通知您</li>
              <li>如审核被拒绝，请根据反馈修改后重新提交</li>
            </ul>
          }
          type="info"
          showIcon
          icon={<InfoCircleOutlined />}
          style={{ marginBottom: '24px', background: '#1E3A5F', border: 'none' }}
        />
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          size="large"
        >
          <Form.Item
            name="title"
            label={<span className="text-white">模板标题</span>}
            rules={[{ required: true, message: '请输入模板标题' }]}
          >
            <Input placeholder="请输入模板标题" style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }} />
          </Form.Item>

          <Form.Item
            name="description"
            label={<span className="text-white">模板描述</span>}
            rules={[{ required: true, message: '请输入模板描述' }]}
          >
            <TextArea
              rows={4}
              placeholder="请详细描述模板的功能和适用场景"
              style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }}
            />
          </Form.Item>

          <div className="grid grid-cols-2 gap-6">
            <Form.Item
              name="category"
              label={<span className="text-white">行业分类</span>}
              rules={[{ required: true, message: '请选择行业分类' }]}
            >
              <Select placeholder="选择分类" style={{ background: '#0F172A' }}>
                {CATEGORIES.map(cat => (
                  <Option key={cat.value} value={cat.value}>{cat.label}</Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="complexity"
              label={<span className="text-white">复杂度</span>}
              rules={[{ required: true, message: '请选择复杂度' }]}
            >
              <Select placeholder="选择复杂度" style={{ background: '#0F172A' }}>
                {COMPLEXITY.map(c => (
                  <Option key={c.value} value={c.value}>{c.label}</Option>
                ))}
              </Select>
            </Form.Item>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <Form.Item
              name="price"
              label={<span className="text-white">价格 (元)</span>}
              initialValue={0}
            >
              <InputNumber
                min={0}
                style={{ width: '100%', background: '#0F172A' }}
                placeholder="0 表示免费"
              />
            </Form.Item>

            <Form.Item
              name="version"
              label={<span className="text-white">版本号</span>}
              initialValue="1.0.0"
            >
              <Input placeholder="1.0.0" style={{ background: '#0F172A', borderColor: '#334155', color: '#fff' }} />
            </Form.Item>
          </div>

          <Form.Item
            name="tags"
            label={<span className="text-white">标签</span>}
          >
            <Select mode="tags" placeholder="输入标签后回车添加" style={{ background: '#0F172A' }} />
          </Form.Item>

          <div className="grid grid-cols-3 gap-6">
            <Form.Item
              label={<span className="text-white">缩略图</span>}
              name="thumbnail"
              valuePropName="fileList"
              getValueFromEvent={normFile}
              rules={[{ required: true, message: '请上传缩略图' }]}
            >
              <Upload
                beforeUpload={(file) => {
                  setThumbnailFile(file as File);
                  return false;
                }}
                maxCount={1}
                accept="image/*"
                listType="picture"
              >
                <Button icon={<UploadOutlined />}>上传缩略图</Button>
              </Upload>
            </Form.Item>

            <Form.Item
              label={<span className="text-white">预览图</span>}
              name="previewImages"
              valuePropName="fileList"
              getValueFromEvent={normFile}
            >
              <Upload
                beforeUpload={(file) => {
                  setPreviewFiles(prev => [...prev, file as File]);
                  return false;
                }}
                multiple
                maxCount={5}
                accept="image/*"
                listType="picture"
              >
                <Button icon={<UploadOutlined />}>上传预览图</Button>
              </Upload>
            </Form.Item>

            <Form.Item
              label={<span className="text-white">模板文件</span>}
              name="file"
              valuePropName="fileList"
              getValueFromEvent={normFile}
              rules={[{ required: true, message: '请上传模板文件' }]}
            >
              <Upload
                beforeUpload={(file) => {
                  setTemplateFile(file as File);
                  return false;
                }}
                maxCount={1}
                accept=".json"
              >
                <Button icon={<UploadOutlined />}>上传JSON文件</Button>
              </Upload>
            </Form.Item>
          </div>

          <Form.Item>
            <div className="flex gap-4">
              <Button type="primary" htmlType="submit" loading={loading} size="large">
                提交审核
              </Button>
              <Button size="large" onClick={() => navigate(-1)}>
                取消
              </Button>
            </div>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default UploadPage;
