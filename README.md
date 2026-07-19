# YL CameraRef

YL CameraRef is a camera reference image tool for Blender. It brings camera creation from the current view, per-camera reference image management, direct viewport adjustments, and composition utilities together in one compact workflow.

Each camera view can have its own collection of reference images. You can quickly switch between different camera views and reference images, making it useful for scene layout, blockouts, modeling, and visual alignment.

### ✨ With YL CameraRef, you can:

- 📷 Quickly create a camera from the current view, supporting both perspective and orthographic views
- 🖼️ Add and manage independent reference images for different cameras
- 🔄 Quickly add, switch, replace, or duplicate multiple reference images on the same camera
- ✋ Move, scale, and rotate reference images directly in the camera view with immediate visual feedback
- 👁️ Quickly control reference image opacity, visibility, and front/back display depth
- 📐 Adjust an object's depth while preserving its composition in the camera frame
- 🎥 Dolly the camera and use Dolly Zoom to preserve the selected subject's size in the frame

---

## Language Support

- Supports English, 简体中文, 繁體中文, 日本語, 한국어, Deutsch, Français, Español, Italiano, Polski, Português, Русский, and Tiếng Việt.

---

## Core Features

### 1. 📷 Quickly Create a Camera from the Current View

- Whether you are in a perspective or orthographic view, you can create a camera directly from the current viewpoint. The new camera matches the current view and immediately enters camera view, giving you exactly what you see. You can also quickly add one from the `Shift+A` menu.

- This is useful for quickly saving the current composition after navigating the scene, finding a suitable angle, or completing viewpoint alignment.

<img width="800" height="450" alt="添加" src="https://github.com/user-attachments/assets/987f002d-9e4f-463c-9d3b-b8596aec3c8a" />


### 2. 🖼️ Quickly Switch Cameras and Directly Adjust Reference Images

#### 2.1 Switch Cameras and Reference Image Workspaces

- Quickly switch between cameras from the list and immediately enter the corresponding camera view. Each camera retains its own collection of reference images, active reference image, and display settings, making it easy to switch between and compare multiple viewpoints.

<img width="800" height="450" alt="切换图" src="https://github.com/user-attachments/assets/bdfb3cec-1b24-46d1-8e04-003f555aee1b" />


#### 2.2 Directly Adjust Reference Images

- After clicking “Adjust,” you can move, scale, and rotate the reference image directly in the camera view. X/Y axis locking, fine adjustments, and snapping are supported. No numerical input is required, and every adjustment is shown directly in the viewport.


<img width="800" height="450" alt="adjust" src="https://github.com/user-attachments/assets/652f04db-5b0e-4df7-a237-76328a49087a" />


### 3. 🧰 CameraRef Tools

CameraRef Tools is a collection of utilities designed around camera composition and reference image alignment. It is hidden by default and can be enabled whenever needed.

#### 3.1 Header Opacity Control

- Display the reference image opacity control in the 3D View header, allowing you to adjust reference image transparency at any time without opening the CameraRef panel.

<img width="800" height="450" alt="快速按钮" src="https://github.com/user-attachments/assets/0eb3e644-44cb-4585-909c-1857a943ba2a" />


#### 3.2 Adjust Object Depth While Preserving Composition (Perspective Cameras Only; Select a Target Mesh First)

- In a perspective camera view, adjust the selected object's forward or backward depth while keeping its appearance in the camera frame unchanged. This makes it easier to adjust scene depth and occlusion relationships.

<img width="800" height="450" alt="物体不变" src="https://github.com/user-attachments/assets/b8d18083-4add-4e21-a131-02b53423eff7" />

#### 3.3 Camera Dolly and Dolly Zoom (Perspective Cameras Only; Select a Target Mesh Before Using Dolly Zoom)

- By default, the current camera can be moved forward or backward along its viewing axis to adjust the distance between the camera and the scene.

- When “Dolly Zoom” is enabled, the focal length is automatically compensated while the camera moves, keeping the selected subject's position and size unchanged in the frame to create a Hitchcock zoom effect.

<img width="800" height="450" alt="希区柯克" src="https://github.com/user-attachments/assets/77f67e45-a8d5-42d8-a634-2856a73fe5a5" />

#### 3.4 ⚙️ Composition and Output Utilities

- CameraRef Tools also provides convenient controls for camera Shift X/Y and matching the render resolution to the reference image resolution.
- 
<img width="723" height="732" alt="QQ20260719-114717" src="https://github.com/user-attachments/assets/9842c64f-d5a1-4f32-ac53-914972f0a61d" />

---

## Getting Started

- Install and enable `YL CameraRef`.
- Press `N` in the 3D View to open the sidebar, then select the `YL CameraRef` tab.

---

## License

- This add-on is licensed under `GPL-3.0-or-later`.
