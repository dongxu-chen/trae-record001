import os
import sys
import numpy as np
import streamlit as st
import cv2
from PIL import Image
import tempfile
import time
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import config, Config
from pipeline.estimator import HumanPoseEstimator3D
from utils.visualization import PoseVisualizer3D

st.set_page_config(
    page_title="3D Human Pose Estimation",
    page_icon="🏃",
    layout="wide"
)

st.title("🏃 3D Human Pose Estimation")
st.markdown("""
基于 HMR + OpenPose 的三维人体姿态估计系统，支持多人检测、时序平滑和全身与手部联合估计。
""")

@st.cache_resource
def load_estimator(custom_config=None):
    if custom_config is None:
        custom_config = config
    return HumanPoseEstimator3D(custom_config)


def configure_sidebar():
    st.sidebar.title("⚙️ Configuration")
    
    st.sidebar.subheader("Model Settings")
    device = st.sidebar.selectbox("Device", ["cpu", "cuda"], 
                                  index=0 if config.DEVICE == "cpu" else 1)
    
    st.sidebar.subheader("Feature Toggles")
    multi_person = st.sidebar.checkbox("Multi-Person Detection", value=config.MULTI_PERSON)
    enable_hand = st.sidebar.checkbox("Enable Hand Estimation", value=config.ENABLE_HAND)
    enable_smoothing = st.sidebar.checkbox("Temporal Smoothing", value=config.ENABLE_TEMPORAL_SMOOTHING)
    
    st.sidebar.subheader("Smoothing Settings")
    smoothing_method = st.sidebar.selectbox(
        "Smoothing Method",
        ["kalman", "exponential", "moving_average"],
        index=["kalman", "exponential", "moving_average"].index(config.smoothing.METHOD)
    )
    alpha = st.sidebar.slider("Smoothing Alpha", 0.1, 0.99, 
                              value=config.smoothing.ALPHA, step=0.05)
    
    st.sidebar.subheader("Tracking Settings")
    max_age = st.sidebar.slider("Max Track Age", 1, 100, 
                                value=config.tracking.MAX_AGE, step=5)
    min_hits = st.sidebar.slider("Min Hits", 1, 20, 
                                 value=config.tracking.MIN_HITS, step=1)
    iou_threshold = st.sidebar.slider("IOU Threshold", 0.1, 0.9, 
                                      value=config.tracking.IOU_THRESHOLD, step=0.05)
    
    st.sidebar.subheader("Visualization")
    show_mesh = st.sidebar.checkbox("Show SMPL Mesh", value=config.visualization.ENABLE_MESH)
    
    custom_config = Config()
    custom_config.DEVICE = device
    custom_config.MULTI_PERSON = multi_person
    custom_config.ENABLE_HAND = enable_hand
    custom_config.ENABLE_TEMPORAL_SMOOTHING = enable_smoothing
    custom_config.smoothing.METHOD = smoothing_method
    custom_config.smoothing.ALPHA = alpha
    custom_config.tracking.MAX_AGE = max_age
    custom_config.tracking.MIN_HITS = min_hits
    custom_config.tracking.IOU_THRESHOLD = iou_threshold
    custom_config.visualization.ENABLE_MESH = show_mesh
    
    return custom_config


def process_image(estimator, uploaded_file):
    file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    if image is None:
        st.error("Failed to load image")
        return None
    
    with st.spinner("Estimating 3D pose..."):
        start_time = time.time()
        result = estimator.process_frame(image)
        inference_time = time.time() - start_time
    
    return result, inference_time


def process_video(estimator, uploaded_file):
    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    tfile.write(uploaded_file.read())
    tfile.close()
    
    cap = cv2.VideoCapture(tfile.name)
    if not cap.isOpened():
        st.error("Failed to open video")
        os.unlink(tfile.name)
        return None
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    output_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    output_path = output_file.name
    output_file.close()
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * 2)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_count = 0
    results = []
    estimator.reset()
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            result = estimator.process_frame(frame, frame_count)
            results.append(result)
            
            if result.image_with_3d is not None:
                writer.write(result.image_with_3d)
            
            frame_count += 1
            progress = min(frame_count / total_frames, 1.0)
            progress_bar.progress(progress)
            status_text.text(f"Processing frame {frame_count}/{total_frames}")
    
    finally:
        cap.release()
        writer.release()
        os.unlink(tfile.name)
    
    return results, output_path


def display_results(result, inference_time=None):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📷 Input Image")
        input_rgb = cv2.cvtColor(result.raw_image, cv2.COLOR_BGR2RGB)
        st.image(input_rgb, use_column_width=True)
    
    with col2:
        st.subheader("📍 2D Keypoints")
        if result.image_with_2d is not None:
            vis_rgb = cv2.cvtColor(result.image_with_2d, cv2.COLOR_BGR2RGB)
            st.image(vis_rgb, use_column_width=True)
    
    if result.image_with_3d is not None:
        st.subheader("🎯 3D Pose Estimation")
        vis_3d_rgb = cv2.cvtColor(result.image_with_3d, cv2.COLOR_BGR2RGB)
        st.image(vis_3d_rgb, use_column_width=True)
    
    if inference_time is not None:
        st.info(f"⏱️ Inference time: {inference_time:.3f} seconds")
    
    if len(result.persons) > 0:
        st.subheader("📊 Results")
        
        for i, person in enumerate(result.persons):
            with st.expander(f"Person {person.track_id} Details"):
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    st.metric("Track ID", person.track_id)
                    st.metric("Reprojection Error", f"{person.reprojection_error:.2f}")
                
                with col_b:
                    st.write("**Shape Parameters (β):**")
                    st.write(person.betas[:5])
                
                with col_c:
                    st.write("**Camera Parameters:**")
                    st.write(f"Scale: {person.camera[0]:.4f}")
                    st.write(f"Translation: ({person.camera[1]:.4f}, {person.camera[2]:.4f})")
                
                st.write("**3D Joints (first 10):**")
                joints_df = {
                    'Joint': ['Pelvis', 'L_Hip', 'R_Hip', 'Spine1', 'L_Knee', 
                             'R_Knee', 'Spine2', 'L_Ankle', 'R_Ankle', 'Spine3'],
                    'X': [f"{x:.3f}" for x in person.joints_3d[:10, 0]],
                    'Y': [f"{y:.3f}" for y in person.joints_3d[:10, 1]],
                    'Z': [f"{z:.3f}" for z in person.joints_3d[:10, 2]]
                }
                st.dataframe(joints_df)


def display_video_results(results, output_path):
    st.subheader("🎬 Processed Video")
    
    if os.path.exists(output_path):
        with open(output_path, 'rb') as f:
            video_bytes = f.read()
        st.video(video_bytes)
    
    st.subheader("📈 Statistics")
    
    num_persons = [len(r.persons) for r in results]
    reprojection_errors = []
    for r in results:
        for p in r.persons:
            reprojection_errors.append(p.reprojection_error)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Frames", len(results))
    with col2:
        st.metric("Avg Persons per Frame", f"{np.mean(num_persons):.1f}")
    with col3:
        if reprojection_errors:
            st.metric("Avg Reprojection Error", f"{np.mean(reprojection_errors):.2f}")
    
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(num_persons)
    ax.set_title("Number of Detected Persons per Frame")
    ax.set_xlabel("Frame")
    ax.set_ylabel("Count")
    ax.grid(True)
    st.pyplot(fig)
    
    if reprojection_errors:
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.plot(reprojection_errors)
        ax2.set_title("Reprojection Error")
        ax2.set_xlabel("Frame")
        ax2.set_ylabel("Error (pixels)")
        ax2.grid(True)
        st.pyplot(fig2)
    
    return output_path


def main():
    custom_config = configure_sidebar()
    
    tab1, tab2, tab3 = st.tabs(["🖼️ Image", "🎥 Video", "ℹ️ About"])
    
    with tab1:
        st.header("Image Processing")
        uploaded_image = st.file_uploader(
            "Upload an image",
            type=['jpg', 'jpeg', 'png', 'bmp'],
            help="Upload an image for 3D human pose estimation"
        )
        
        if uploaded_image is not None:
            estimator = load_estimator(custom_config)
            result, inference_time = process_image(estimator, uploaded_image)
            if result is not None:
                display_results(result, inference_time)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Reset Estimator", key="reset_image"):
                        estimator.reset()
                        st.success("Estimator reset!")
                
                with col2:
                    if st.button("💾 Save Results", key="save_image"):
                        save_dir = "output"
                        os.makedirs(save_dir, exist_ok=True)
                        base_name = os.path.splitext(uploaded_image.name)[0]
                        if result.image_with_3d is not None:
                            cv2.imwrite(f"{save_dir}/{base_name}_3d.jpg", result.image_with_3d)
                        np.save(f"{save_dir}/{base_name}_joints.npy", 
                                [p.joints_3d for p in result.persons])
                        st.success(f"Results saved to {save_dir}/")
    
    with tab2:
        st.header("Video Processing")
        uploaded_video = st.file_uploader(
            "Upload a video",
            type=['mp4', 'avi', 'mov', 'mkv'],
            help="Upload a video for 3D human pose estimation"
        )
        
        max_frames = st.slider("Max Frames to Process", 10, 1000, 100, 10)
        
        if uploaded_video is not None:
            estimator = load_estimator(custom_config)
            
            if st.button("▶️ Process Video", key="process_video"):
                with st.spinner("Processing video..."):
                    results, output_path = process_video(estimator, uploaded_video)
                
                if results is not None:
                    output_path = display_video_results(results, output_path)
                    
                    st.download_button(
                        label="⬇️ Download Processed Video",
                        data=open(output_path, 'rb').read(),
                        file_name="processed_video.mp4",
                        mime="video/mp4"
                    )
                    
                    if st.button("🗑️ Cleanup", key="cleanup_video"):
                        if os.path.exists(output_path):
                            os.unlink(output_path)
                        st.success("Cleanup complete!")
    
    with tab3:
        st.header("About")
        
        st.markdown("""
        ## 3D Human Pose Estimation System
        
        This system implements 3D human pose estimation from single images or videos using:
        
        ### 🏗️ Architecture
        - **HMR (Human Mesh Recovery)**: Regresses SMPL parameters from images
        - **SMPL**: Parametric human body model
        - **OpenPose**: 2D keypoint detection for body and hands
        - **Multi-person Tracking**: Kalman filter + Hungarian algorithm
        - **Temporal Smoothing**: Kalman filtering for smooth video results
        
        ### ✨ Features
        - ✅ Single image 3D pose estimation
        - ✅ Multi-person detection and tracking
        - ✅ Hand keypoint estimation
        - ✅ Temporal smoothing for videos
        - ✅ 3D visualization with SMPL mesh
        - ✅ Reprojection error calculation
        
        ### 📦 Model Weights Required
        Before using, please download:
        
        1. **SMPL Model**: `models/smpl/basicModel_neutral_lbs_10_207_0_v1.0.0.pkl`
           - Download from: https://smpl.is.tue.mpg.de/
        
        2. **HMR Checkpoint**: `models/hmr/hmr_pretrained.pt`
           - Download from: https://github.com/akanazawa/hmr
        
        3. **OpenPose Models**:
           - Body: `models/openpose/pose_deploy_linevec.prototxt` + `pose_iter_440000.caffemodel`
           - Hand: `models/openpose/pose_deploy.prototxt` + `pose_iter_102000.caffemodel`
           - Download from: https://github.com/CMU-Perceptual-Computing-Lab/openpose
        
        ### 🔧 Usage
        1. Configure settings in the sidebar
        2. Upload an image or video
        3. View the 2D keypoints and 3D pose estimation
        4. Save results if needed
        
        ### 📚 References
        - HMR: [End-to-End Recovery of Human Shape and Pose](https://arxiv.org/abs/1712.06584)
        - SMPL: [A Skinned Multi-Person Linear Model](https://smpl.is.tue.mpg.de/)
        - OpenPose: [Realtime Multi-Person 2D Pose Estimation](https://arxiv.org/abs/1611.08050)
        """)


if __name__ == "__main__":
    main()
