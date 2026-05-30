import { useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { TransformControls } from 'three/examples/jsm/controls/TransformControls.js';
import { CsgCutter } from '../utils/CsgCutter.js';
import { PlaneManager } from '../utils/PlaneManager.js';
import { CurveCutter } from '../utils/CurveCutter.js';
import { CutFiller } from '../utils/CutFiller.js';
import { CutAnimator } from '../utils/CutAnimator.js';
import { Brush as CsgBrush, SUBTRACTION, INTERSECTION } from 'three-bvh-csg';

export default function Scene({
  modelGroup,
  modelBounds,
  onCutComplete,
  showPreview,
  cutPieces,
  showPieces,
  onStatusChange,
  drawingMode,
  fillEnabled,
  fillType,
  fillDensity,
  showAnimation,
  onAnimationStateChange
}) {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const cameraRef = useRef(null);
  const rendererRef = useRef(null);
  const controlsRef = useRef(null);
  const transformControlsRef = useRef(null);
  const planeManagerRef = useRef(null);
  const csgCutterRef = useRef(null);
  const cutPiecesGroupRef = useRef(null);
  const previewPiecesGroupRef = useRef(null);
  const fillGroupRef = useRef(null);
  const raycasterRef = useRef(new THREE.Raycaster());
  const mouseRef = useRef(new THREE.Vector2());
  const isDraggingPlaneRef = useRef(false);
  const dragPlaneRef = useRef(null);
  const dragOffsetRef = useRef(0);
  const animationIdRef = useRef(null);
  const modelRenderedRef = useRef(false);
  const curveCutterRef = useRef(null);
  const cutFillerRef = useRef(null);
  const cutAnimatorRef = useRef(null);

  const initScene = useCallback(() => {
    if (!containerRef.current || sceneRef.current) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      60,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(6, 6, 6);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.localClippingEnabled = true;
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 2;
    controls.maxDistance = 50;
    controlsRef.current = controls;

    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(10, 15, 10);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    scene.add(directionalLight);

    const pointLight1 = new THREE.PointLight(0x4fc3f7, 0.5);
    pointLight1.position.set(-8, 5, -8);
    scene.add(pointLight1);

    const pointLight2 = new THREE.PointLight(0xffb74d, 0.3);
    pointLight2.position.set(8, 5, 8);
    scene.add(pointLight2);

    const gridHelper = new THREE.GridHelper(20, 20, 0x0f3460, 0x0f3460);
    gridHelper.position.y = -0.01;
    scene.add(gridHelper);

    const axesHelper = new THREE.AxesHelper(3);
    scene.add(axesHelper);

    const transformControls = new TransformControls(camera, renderer.domElement);
    transformControls.setMode('translate');
    transformControls.addEventListener('dragging-changed', (event) => {
      controls.enabled = !event.value;
    });
    transformControls.addEventListener('objectChange', () => {
      if (transformControls.object && planeManagerRef.current) {
        const activePlane = planeManagerRef.current.getActivePlane();
        if (activePlane && activePlane.mesh === transformControls.object) {
          const plane = activePlane.plane;
          const normal = plane.normal.clone();
          const position = transformControls.object.position.clone();
          const center = modelBounds.getCenter(new THREE.Vector3());
          const offset = position.clone().sub(center);
          const constant = -normal.dot(offset);
          plane.constant = constant;
          
          if (showPreview && modelGroup) {
            updateCutPreview();
          }
        }
      }
    });
    scene.add(transformControls);
    transformControlsRef.current = transformControls;

    const cutPiecesGroup = new THREE.Group();
    cutPiecesGroup.name = 'cutPieces';
    cutPiecesGroup.visible = false;
    scene.add(cutPiecesGroup);
    cutPiecesGroupRef.current = cutPiecesGroup;

    const previewPiecesGroup = new THREE.Group();
    previewPiecesGroup.name = 'previewPieces';
    previewPiecesGroup.visible = false;
    scene.add(previewPiecesGroup);
    previewPiecesGroupRef.current = previewPiecesGroup;

    const fillGroup = new THREE.Group();
    fillGroup.name = 'fillStructures';
    fillGroup.visible = true;
    scene.add(fillGroup);
    fillGroupRef.current = fillGroup;

    planeManagerRef.current = new PlaneManager(scene, modelBounds || new THREE.Box3());
    csgCutterRef.current = new CsgCutter();
    curveCutterRef.current = new CurveCutter();
    cutFillerRef.current = new CutFiller();
    cutAnimatorRef.current = new CutAnimator(scene, camera, renderer);

    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!containerRef.current) return;
      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    window.addEventListener('resize', handleResize);

    renderer.domElement.addEventListener('mousedown', onMouseDown);
    renderer.domElement.addEventListener('mousemove', onMouseMove);
    renderer.domElement.addEventListener('mouseup', onMouseUp);
    renderer.domElement.addEventListener('dblclick', onDoubleClick);

    return () => {
      window.removeEventListener('resize', handleResize);
      renderer.domElement.removeEventListener('mousedown', onMouseDown);
      renderer.domElement.removeEventListener('mousemove', onMouseMove);
      renderer.domElement.removeEventListener('mouseup', onMouseUp);
      renderer.domElement.removeEventListener('dblclick', onDoubleClick);
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, [modelBounds, showPreview, modelGroup]);

  const onMouseDown = useCallback((event) => {
    if (!containerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    mouseRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouseRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current);

    if (drawingMode && curveCutterRef.current && modelGroup) {
      const modelMeshes = [];
      modelGroup.traverse(child => { if (child.isMesh) modelMeshes.push(child); });
      const intersects = raycasterRef.current.intersectObjects(modelMeshes, false);
      
      if (intersects.length > 0) {
        const hit = intersects[0];
        const faceNormal = hit.face?.normal
          ? hit.face.normal.clone().transformDirection(hit.object.matrixWorld)
          : new THREE.Vector3(0, 1, 0);
        curveCutterRef.current.addPoint(hit.point, faceNormal);
        if (onStatusChange) {
          onStatusChange(`曲线绘制中... 已添加 ${curveCutterRef.current.getPointCount()} 个点`);
        }
      }
      return;
    }

    if (!planeManagerRef.current) return;

    const planeMeshes = planeManagerRef.current.planeMeshes.filter(m => m.visible);
    const intersects = raycasterRef.current.intersectObjects(planeMeshes, false);

    if (intersects.length > 0) {
      const clickedMesh = intersects[0].object;
      const planeIndex = planeManagerRef.current.planeMeshes.indexOf(clickedMesh);

      if (planeIndex >= 0) {
        planeManagerRef.current.setActivePlane(planeIndex);

        if (transformControlsRef.current) {
          transformControlsRef.current.attach(clickedMesh);
        }

        isDraggingPlaneRef.current = true;
        dragPlaneRef.current = planeManagerRef.current.planes[planeIndex];

        const planePoint = intersects[0].point;
        const normal = dragPlaneRef.current.normal.clone();
        const center = modelBounds.getCenter(new THREE.Vector3());
        const offset = planePoint.clone().sub(center);
        dragOffsetRef.current = normal.dot(offset) + dragPlaneRef.current.constant;

        if (controlsRef.current) {
          controlsRef.current.enabled = false;
        }

        if (onStatusChange) {
          onStatusChange('拖拽平面调整切割位置');
        }
      }
    }
  }, [modelBounds, onStatusChange, drawingMode, modelGroup]);

  const onMouseMove = useCallback((event) => {
    if (isDraggingPlaneRef.current && dragPlaneRef.current && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      mouseRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouseRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

      raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current);

      const normal = dragPlaneRef.current.normal.clone();
      const center = modelBounds.getCenter(new THREE.Vector3());
      const planePointOnRay = center.clone().add(normal.clone().multiplyScalar(-dragPlaneRef.current.constant));

      const dragPlane = new THREE.Plane(normal, -normal.dot(planePointOnRay));
      const intersectPoint = new THREE.Vector3();
      raycasterRef.current.ray.intersectPlane(dragPlane, intersectPoint);

      if (intersectPoint) {
        const offset = intersectPoint.clone().sub(center);
        let constant = -normal.dot(offset) + dragOffsetRef.current;

        const size = modelBounds.getSize(new THREE.Vector3());
        const maxOffset = Math.max(size.x, size.y, size.z) * 1.5;
        constant = Math.max(-maxOffset, Math.min(maxOffset, constant));

        const activeIndex = planeManagerRef.current.activePlaneIndex;
        planeManagerRef.current.updatePlaneConstant(activeIndex, constant);

        if (showPreview && modelGroup) {
          updateCutPreview();
        }
      }
    }
  }, [modelBounds, showPreview, modelGroup]);

  const onMouseUp = useCallback(() => {
    isDraggingPlaneRef.current = false;
    dragPlaneRef.current = null;

    if (controlsRef.current) {
      controlsRef.current.enabled = true;
    }

    if (onStatusChange) {
      onStatusChange('就绪');
    }
  }, [onStatusChange]);

  const onDoubleClick = useCallback((event) => {
    if (drawingMode || !containerRef.current || !planeManagerRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    mouseRef.current.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    mouseRef.current.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    raycasterRef.current.setFromCamera(mouseRef.current, cameraRef.current);

    const planeMeshes = planeManagerRef.current.planeMeshes.filter(m => m.visible);
    const intersects = raycasterRef.current.intersectObjects(planeMeshes, false);

    if (intersects.length > 0) {
      const clickedMesh = intersects[0].object;
      const planeIndex = planeManagerRef.current.planeMeshes.indexOf(clickedMesh);

      if (planeIndex >= 0) {
        planeManagerRef.current.flipPlane(planeIndex);

        if (showPreview && modelGroup) {
          updateCutPreview();
        }
      }
    }
  }, [drawingMode, showPreview, modelGroup]);

  const updateCutPreview = useCallback(() => {
    if (!modelGroup || !csgCutterRef.current || !planeManagerRef.current) return;
    if (!previewPiecesGroupRef.current) return;

    while (previewPiecesGroupRef.current.children.length > 0) {
      const child = previewPiecesGroupRef.current.children[0];
      previewPiecesGroupRef.current.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach(m => m.dispose());
        } else {
          child.material.dispose();
        }
      }
    }

    const planes = planeManagerRef.current.planes;
    if (planes.length === 0) return;

    modelGroup.traverse((child) => {
      if (child.isMesh) {
        const pieces = csgCutterRef.current.cutMeshByMultiplePlanes(child, planes, modelBounds);

        pieces.forEach((piece, idx) => {
          piece.material = new THREE.MeshStandardMaterial({
            color: piece.material?.color?.getHex() || 0x4fc3f7,
            metalness: 0.1,
            roughness: 0.5,
            side: THREE.DoubleSide,
            transparent: true,
            opacity: 0.7,
            depthWrite: true,
            polygonOffset: true,
            polygonOffsetFactor: 1,
            polygonOffsetUnit: 1
          });

          const wireframeMat = new THREE.MeshBasicMaterial({
            color: piece.material?.color?.getHex() || 0x4fc3f7,
            wireframe: true,
            transparent: true,
            opacity: 0.15,
            side: THREE.DoubleSide,
            depthWrite: false,
            polygonOffset: true,
            polygonOffsetFactor: -1,
            polygonOffsetUnit: -1
          });
          const wireframeMesh = new THREE.Mesh(piece.geometry.clone(), wireframeMat);
          piece.add(wireframeMesh);

          piece.position.x += (idx % 2 === 0 ? -0.5 : 0.5) * 0.3;
          piece.position.z += (idx % 3 === 0 ? 0 : (idx % 3 === 1 ? 0.3 : -0.3)) * 0.2;
          piece.renderOrder = idx;
          previewPiecesGroupRef.current.add(piece);
        });
      }
    });

    previewPiecesGroupRef.current.visible = true;
    if (modelGroup) modelGroup.visible = false;
  }, [modelGroup, modelBounds]);

  useEffect(() => {
    const cleanup = initScene();
    return cleanup;
  }, [initScene]);

  useEffect(() => {
    if (planeManagerRef.current && modelBounds) {
      planeManagerRef.current.updateModelBounds(modelBounds);
    }
  }, [modelBounds]);

  useEffect(() => {
    if (!sceneRef.current || !modelGroup) return;

    if (modelRenderedRef.current) {
      const oldGroup = sceneRef.current.getObjectByName('loadedModel');
      if (oldGroup) {
        sceneRef.current.remove(oldGroup);
      }
    }

    modelGroup.name = 'loadedModel';
    sceneRef.current.add(modelGroup);
    modelRenderedRef.current = true;

    if (previewPiecesGroupRef.current) {
      while (previewPiecesGroupRef.current.children.length > 0) {
        const child = previewPiecesGroupRef.current.children[0];
        previewPiecesGroupRef.current.remove(child);
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
      }
      previewPiecesGroupRef.current.visible = false;
    }

    if (cutPiecesGroupRef.current) {
      while (cutPiecesGroupRef.current.children.length > 0) {
        const child = cutPiecesGroupRef.current.children[0];
        cutPiecesGroupRef.current.remove(child);
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
      }
      cutPiecesGroupRef.current.visible = false;
    }

    if (fillGroupRef.current) {
      while (fillGroupRef.current.children.length > 0) {
        const child = fillGroupRef.current.children[0];
        fillGroupRef.current.remove(child);
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
      }
    }

    if (planeManagerRef.current) {
      planeManagerRef.current.clearAll();
    }

    if (curveCutterRef.current) {
      curveCutterRef.current.clearDrawing();
    }

    if (modelGroup) modelGroup.visible = true;

  }, [modelGroup]);

  useEffect(() => {
    if (showPreview && modelGroup) {
      updateCutPreview();
    } else if (previewPiecesGroupRef.current) {
      previewPiecesGroupRef.current.visible = false;
      if (modelGroup) modelGroup.visible = true;
    }
  }, [showPreview, updateCutPreview, modelGroup]);

  useEffect(() => {
    if (controlsRef.current) {
      controlsRef.current.enabled = !drawingMode;
    }
  }, [drawingMode]);

  useEffect(() => {
    if (!cutPiecesGroupRef.current) return;

    while (cutPiecesGroupRef.current.children.length > 0) {
      const child = cutPiecesGroupRef.current.children[0];
      cutPiecesGroupRef.current.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
    }

    if (showPieces && cutPieces && cutPieces.length > 0) {
      const spacing = 1.2;
      const cols = Math.ceil(Math.sqrt(cutPieces.length));

      cutPieces.forEach((piece, idx) => {
        const pieceCopy = piece.clone();
        const row = Math.floor(idx / cols);
        const col = idx % cols;
        const centerOffset = (cols - 1) / 2;
        pieceCopy.position.x = (col - centerOffset) * spacing;
        pieceCopy.position.z = (row - centerOffset) * spacing;
        pieceCopy.name = `piece_${idx + 1}`;
        cutPiecesGroupRef.current.add(pieceCopy);
      });

      cutPiecesGroupRef.current.visible = true;
      if (previewPiecesGroupRef.current) {
        previewPiecesGroupRef.current.visible = false;
      }
      if (modelGroup) modelGroup.visible = false;
    } else {
      cutPiecesGroupRef.current.visible = false;
      if (!showPreview && modelGroup) {
        modelGroup.visible = true;
      }
    }
  }, [cutPieces, showPieces, showPreview, modelGroup]);

  const addPlane = useCallback((normal) => {
    if (!planeManagerRef.current) return null;
    return planeManagerRef.current.addPlane(normal);
  }, []);

  const removePlane = useCallback((index) => {
    if (!planeManagerRef.current) return false;

    if (transformControlsRef.current) {
      transformControlsRef.current.detach();
    }

    const result = planeManagerRef.current.removePlane(index);

    if (showPreview && modelGroup) {
      updateCutPreview();
    }

    return result;
  }, [showPreview, modelGroup, updateCutPreview]);

  const performCut = useCallback((options = {}) => {
    if (!modelGroup || !csgCutterRef.current || !planeManagerRef.current) {
      return [];
    }

    const planes = planeManagerRef.current.planes;
    if (planes.length === 0) {
      return [];
    }

    const allPieces = [];

    modelGroup.traverse((child) => {
      if (child.isMesh) {
        const pieces = csgCutterRef.current.cutMeshByMultiplePlanes(child, planes, modelBounds, options);
        pieces.forEach((piece, idx) => {
          piece.name = `切块 ${allPieces.length + 1}`;
          piece.material = new THREE.MeshStandardMaterial({
            color: piece.material?.color?.getHex() || 0x4fc3f7,
            metalness: 0.1,
            roughness: 0.5,
            side: THREE.DoubleSide,
            depthWrite: true,
            polygonOffset: true,
            polygonOffsetFactor: 1,
            polygonOffsetUnit: 1
          });
          allPieces.push(piece);
        });
      }
    });

    if (fillEnabled && cutFillerRef.current && fillGroupRef.current) {
      while (fillGroupRef.current.children.length > 0) {
        const child = fillGroupRef.current.children[0];
        fillGroupRef.current.remove(child);
        if (child.geometry) child.geometry.dispose();
        if (child.material) child.material.dispose();
      }

      allPieces.forEach(piece => {
        planes.forEach(plane => {
          const fill = cutFillerRef.current.generateFill(piece, plane, modelBounds, {
            fillType: fillType || 'grid',
            fillDensity: fillDensity || 5,
            fillThickness: 0.03,
            fillDepth: 0.15
          });
          if (fill) {
            fillGroupRef.current.add(fill);
          }
        });
      });
    }

    if (onCutComplete) {
      onCutComplete(allPieces);
    }

    return allPieces;
  }, [modelGroup, modelBounds, onCutComplete, fillEnabled, fillType, fillDensity]);

  const performCurveCut = useCallback((options = {}) => {
    if (!modelGroup || !csgCutterRef.current || !curveCutterRef.current) {
      return [];
    }

    if (curveCutterRef.current.getPointCount() < 3) {
      if (onStatusChange) onStatusChange('曲线点数不足，至少需要3个点');
      return [];
    }

    const cutBrushMesh = curveCutterRef.current.createExtrudedCutBrush(modelBounds);
    if (!cutBrushMesh) {
      if (onStatusChange) onStatusChange('曲线切割面生成失败');
      return [];
    }

    const allPieces = [];

    modelGroup.traverse((child) => {
      if (child.isMesh) {
        const sourceBrush = csgCutterRef.current.createBrushFromMesh(child);
        if (!sourceBrush) return;

        cutBrushMesh.updateMatrixWorld(true);
        const cutBrush = new CsgBrush(
          cutBrushMesh.geometry.clone(),
          cutBrushMesh.material.clone(),
          cutBrushMesh.matrixWorld
        );

        try {
          csgCutterRef.current.evaluator.useGroups = true;

          const remaining = csgCutterRef.current.evaluator.evaluate(sourceBrush, cutBrush, SUBTRACTION);
          if (remaining?.geometry?.getAttribute('position')?.count > 0) {
            const remainingMesh = csgCutterRef.current.createMeshFromResult(remaining, 0x4fc3f7);
            if (remainingMesh) {
              remainingMesh.name = `切块 ${allPieces.length + 1}`;
              remainingMesh.material.side = THREE.DoubleSide;
              allPieces.push(remainingMesh);
            }
          }

          const cutout = csgCutterRef.current.evaluator.evaluate(sourceBrush, cutBrush, INTERSECTION);
          if (cutout?.geometry?.getAttribute('position')?.count > 0) {
            const cutoutMesh = csgCutterRef.current.createMeshFromResult(cutout, 0xffb74d);
            if (cutoutMesh) {
              cutoutMesh.name = `切块 ${allPieces.length + 1}`;
              cutoutMesh.material.side = THREE.DoubleSide;
              allPieces.push(cutoutMesh);
            }
          }
        } catch (error) {
          console.error('曲线切割失败:', error);
        }
      }
    });

    if (fillEnabled && cutFillerRef.current && fillGroupRef.current && allPieces.length > 0) {
      const positions = curveCutterRef.current.getCurvePoints();
      if (positions.length >= 3) {
        const curve = new THREE.CatmullRomCurve3(positions);
        const tangent = curve.getTangentAt(0.5);
        const fillPlane = new THREE.Plane().setFromNormalAndCoplanarPoint(tangent, curve.getPointAt(0.5));

        allPieces.forEach(piece => {
          const fill = cutFillerRef.current.generateFill(piece, fillPlane, modelBounds, {
            fillType: fillType || 'grid',
            fillDensity: fillDensity || 5,
            fillThickness: 0.03,
            fillDepth: 0.15
          });
          if (fill) {
            fillGroupRef.current.add(fill);
          }
        });
      }
    }

    curveCutterRef.current.clearDrawing();

    if (onCutComplete) {
      onCutComplete(allPieces);
    }

    return allPieces;
  }, [modelGroup, modelBounds, onCutComplete, onStatusChange, fillEnabled, fillType, fillDensity]);

  const startCurveDrawing = useCallback(() => {
    if (!curveCutterRef.current || !sceneRef.current) return;
    curveCutterRef.current.startDrawing(sceneRef.current);
    if (onStatusChange) onStatusChange('曲线绘制模式 - 在模型表面点击添加点');
  }, [onStatusChange]);

  const stopCurveDrawing = useCallback(() => {
    if (!curveCutterRef.current) return;
    curveCutterRef.current.stopDrawing();
    if (onStatusChange) onStatusChange('就绪');
  }, [onStatusChange]);

  const clearCurveDrawing = useCallback(() => {
    if (!curveCutterRef.current) return;
    curveCutterRef.current.clearDrawing();
    if (onStatusChange) onStatusChange('曲线已清除');
  }, [onStatusChange]);

  const playCutAnimation = useCallback((pieces, animOptions = {}) => {
    if (!cutAnimatorRef.current || !modelGroup) return;

    const firstPlane = planeManagerRef.current?.planes?.[0] || null;

    cutAnimatorRef.current.startAnimation(modelGroup, pieces, firstPlane, {
      duration: animOptions.duration || 2.0,
      speed: animOptions.speed || 1.0,
      separationDistance: animOptions.separationDistance || 1.5,
      showGlow: true,
      showParticles: true,
      onComplete: () => {
        if (onAnimationStateChange) onAnimationStateChange('completed');
        if (onStatusChange) onStatusChange('切割动画完成');
      },
      onProgress: (progress) => {
        if (onAnimationStateChange) onAnimationStateChange(`playing:${Math.round(progress * 100)}`);
      }
    });

    if (onStatusChange) onStatusChange('播放切割动画...');
  }, [modelGroup, onStatusChange, onAnimationStateChange]);

  const stopCutAnimation = useCallback(() => {
    if (!cutAnimatorRef.current) return;
    cutAnimatorRef.current.stopAnimation();
    if (onAnimationStateChange) onAnimationStateChange('stopped');
  }, [onAnimationStateChange]);

  const setPlaneVisibility = useCallback((index, visible) => {
    if (planeManagerRef.current) {
      planeManagerRef.current.setPlaneVisibility(index, visible);
    }
  }, []);

  const setAllPlanesVisibility = useCallback((visible) => {
    if (planeManagerRef.current) {
      planeManagerRef.current.setAllPlanesVisibility(visible);
    }
  }, []);

  const getPlanes = useCallback(() => {
    if (!planeManagerRef.current) return [];
    return planeManagerRef.current.getAllPlanes();
  }, []);

  const getActivePlane = useCallback(() => {
    if (!planeManagerRef.current) return null;
    return planeManagerRef.current.getActivePlane();
  }, []);

  const rotatePlane = useCallback((index, axis, angle) => {
    if (planeManagerRef.current) {
      planeManagerRef.current.rotatePlane(index, axis, angle);
      if (showPreview && modelGroup) {
        updateCutPreview();
      }
    }
  }, [showPreview, modelGroup, updateCutPreview]);

  const flipPlane = useCallback((index) => {
    if (planeManagerRef.current) {
      planeManagerRef.current.flipPlane(index);
      if (showPreview && modelGroup) {
        updateCutPreview();
      }
    }
  }, [showPreview, modelGroup, updateCutPreview]);

  const resetPlane = useCallback((index) => {
    if (planeManagerRef.current) {
      planeManagerRef.current.resetPlane(index);
      if (showPreview && modelGroup) {
        updateCutPreview();
      }
    }
  }, [showPreview, modelGroup, updateCutPreview]);

  useEffect(() => {
    if (window) {
      window.__sceneApi = {
        addPlane,
        removePlane,
        performCut,
        performCurveCut,
        setPlaneVisibility,
        setAllPlanesVisibility,
        getPlanes,
        getActivePlane,
        rotatePlane,
        flipPlane,
        resetPlane,
        startCurveDrawing,
        stopCurveDrawing,
        clearCurveDrawing,
        playCutAnimation,
        stopCutAnimation
      };
    }

    return () => {
      if (window) {
        delete window.__sceneApi;
      }
    };
  }, [addPlane, removePlane, performCut, performCurveCut, setPlaneVisibility, setAllPlanesVisibility, getPlanes, getActivePlane, rotatePlane, flipPlane, resetPlane, startCurveDrawing, stopCurveDrawing, clearCurveDrawing, playCutAnimation, stopCutAnimation]);

  return (
    <div 
      ref={containerRef} 
      style={{ width: '100%', height: '100%', cursor: drawingMode ? 'crosshair' : 'default' }}
    />
  );
}
