using UnityEngine;

public enum CameraMode
{
    Indoor,
    Outdoor
}

[RequireComponent(typeof(CharacterController))]
public class CameraController : MonoBehaviour
{
    [Header("Mode Settings")]
    public CameraMode currentMode = CameraMode.Indoor;
    public KeyCode modeSwitchKey = KeyCode.Tab;
    
    [Header("Outdoor Mode Settings")]
    public float outdoorMoveSpeed = 8.0f;
    public float outdoorJumpSpeed = 10.0f;
    public float outdoorGravity = 25.0f;
    public float outdoorMouseSensitivity = 100.0f;
    public Vector3 outdoorCameraOffset = new Vector3(0.0f, 1.6f, 0.0f);
    public float outdoorCameraSmoothSpeed = 8.0f;
    public bool outdoorEnableJump = true;
    
    [Header("Indoor Mode Settings")]
    public float indoorMoveSpeed = 4.0f;
    public float indoorGravity = 20.0f;
    public float indoorMouseSensitivity = 80.0f;
    public Vector3 indoorCameraOffset = new Vector3(0.0f, 1.7f, 0.0f);
    public float indoorCameraSmoothSpeed = 12.0f;
    public bool indoorEnableJump = false;
    public bool indoorEnableHeadBob = true;
    
    [Header("Head Bob Settings")]
    public float headBobFrequency = 1.5f;
    public float headBobAmplitude = 0.05f;
    public float headBobSmoothSpeed = 10.0f;
    
    [Header("Slope Settings")]
    public float slopeLimit = 45.0f;
    public float stepOffset = 0.3f;
    public bool enableSlopeStabilization = true;
    public float maxSlopeAngle = 45.0f;
    
    [Header("Mouse Settings")]
    public float minPitch = -90.0f;
    public float maxPitch = 90.0f;
    
    [Header("Camera Settings")]
    public Transform cameraTransform;
    
    private CharacterController controller;
    private Vector3 moveDirection = Vector3.zero;
    private float yaw = 0.0f;
    private float pitch = 0.0f;
    private Vector3 currentVelocity;
    private float headBobPhase = 0.0f;
    private Vector3 headBobOffset = Vector3.zero;
    
    private float currentMoveSpeed;
    private float currentJumpSpeed;
    private float currentGravity;
    private float currentMouseSensitivity;
    private Vector3 currentCameraOffset;
    private float currentCameraSmoothSpeed;
    private bool currentEnableJump;
    
    void Start()
    {
        controller = GetComponent<CharacterController>();
        controller.slopeLimit = slopeLimit;
        controller.stepOffset = stepOffset;
        
        if (cameraTransform == null)
        {
            Camera mainCamera = Camera.main;
            if (mainCamera != null)
            {
                cameraTransform = mainCamera.transform;
            }
        }
        
        ApplyModeSettings(currentMode);
        
        Cursor.lockState = CursorLockMode.Locked;
        Cursor.visible = false;
    }
    
    void Update()
    {
        HandleModeSwitch();
        HandleMouseRotation();
        HandleMovement();
        UpdateHeadBob();
        StabilizeCamera();
    }
    
    void HandleModeSwitch()
    {
        if (Input.GetKeyDown(modeSwitchKey))
        {
            currentMode = currentMode == CameraMode.Indoor ? CameraMode.Outdoor : CameraMode.Indoor;
            ApplyModeSettings(currentMode);
        }
    }
    
    void ApplyModeSettings(CameraMode mode)
    {
        if (mode == CameraMode.Outdoor)
        {
            currentMoveSpeed = outdoorMoveSpeed;
            currentJumpSpeed = outdoorJumpSpeed;
            currentGravity = outdoorGravity;
            currentMouseSensitivity = outdoorMouseSensitivity;
            currentCameraOffset = outdoorCameraOffset;
            currentCameraSmoothSpeed = outdoorCameraSmoothSpeed;
            currentEnableJump = outdoorEnableJump;
        }
        else
        {
            currentMoveSpeed = indoorMoveSpeed;
            currentJumpSpeed = 0f;
            currentGravity = indoorGravity;
            currentMouseSensitivity = indoorMouseSensitivity;
            currentCameraOffset = indoorCameraOffset;
            currentCameraSmoothSpeed = indoorCameraSmoothSpeed;
            currentEnableJump = indoorEnableJump;
        }
    }
    
    void HandleMouseRotation()
    {
        float mouseX = Input.GetAxis("Mouse X") * currentMouseSensitivity * Time.deltaTime;
        float mouseY = Input.GetAxis("Mouse Y") * currentMouseSensitivity * Time.deltaTime;
        
        yaw += mouseX;
        pitch -= mouseY;
        pitch = Mathf.Clamp(pitch, minPitch, maxPitch);
        
        transform.localRotation = Quaternion.Euler(0.0f, yaw, 0.0f);
        
        if (cameraTransform != null)
        {
            cameraTransform.localRotation = Quaternion.Euler(pitch, 0.0f, 0.0f);
        }
    }
    
    void HandleMovement()
    {
        if (controller.isGrounded)
        {
            float horizontal = Input.GetAxis("Horizontal");
            float vertical = Input.GetAxis("Vertical");
            
            Vector3 inputDirection = new Vector3(horizontal, 0.0f, vertical);
            inputDirection = transform.TransformDirection(inputDirection);
            inputDirection = Vector3.ClampMagnitude(inputDirection, 1.0f);
            
            moveDirection = inputDirection * currentMoveSpeed;
            
            if (enableSlopeStabilization)
            {
                moveDirection = AdjustForSlope(moveDirection);
            }
            
            if (currentEnableJump && Input.GetButton("Jump"))
            {
                moveDirection.y = currentJumpSpeed;
            }
            else
            {
                moveDirection.y = -1.0f;
            }
        }
        
        moveDirection.y -= currentGravity * Time.deltaTime;
        controller.Move(moveDirection * Time.deltaTime);
    }
    
    void UpdateHeadBob()
    {
        if (!indoorEnableHeadBob || currentMode != CameraMode.Indoor)
        {
            headBobOffset = Vector3.Lerp(headBobOffset, Vector3.zero, headBobSmoothSpeed * Time.deltaTime);
            return;
        }
        
        bool isMoving = controller.isGrounded && (Mathf.Abs(Input.GetAxis("Horizontal")) > 0.1f || Mathf.Abs(Input.GetAxis("Vertical")) > 0.1f);
        
        if (isMoving)
        {
            headBobPhase += headBobFrequency * Time.deltaTime * currentMoveSpeed;
            float bobY = Mathf.Sin(headBobPhase) * headBobAmplitude;
            float bobX = Mathf.Cos(headBobPhase * 0.5f) * headBobAmplitude * 0.5f;
            Vector3 targetBob = new Vector3(bobX, bobY, 0f);
            headBobOffset = Vector3.Lerp(headBobOffset, targetBob, headBobSmoothSpeed * Time.deltaTime);
        }
        else
        {
            headBobOffset = Vector3.Lerp(headBobOffset, Vector3.zero, headBobSmoothSpeed * Time.deltaTime);
        }
    }
    
    Vector3 AdjustForSlope(Vector3 movement)
    {
        if (Physics.Raycast(transform.position, Vector3.down, out RaycastHit hit, controller.height * 0.5f + 0.1f))
        {
            float slopeAngle = Vector3.Angle(hit.normal, Vector3.up);
            
            if (slopeAngle > 0.1f && slopeAngle <= maxSlopeAngle)
            {
                Vector3 projectedMovement = Vector3.ProjectOnPlane(movement, hit.normal);
                projectedMovement = Vector3.ClampMagnitude(projectedMovement, movement.magnitude);
                return projectedMovement;
            }
        }
        
        return movement;
    }
    
    void StabilizeCamera()
    {
        if (cameraTransform == null)
            return;
        
        Vector3 desiredPosition = transform.position + currentCameraOffset + headBobOffset;
        
        if (currentCameraSmoothSpeed > 0.0f)
        {
            cameraTransform.position = Vector3.SmoothDamp(
                cameraTransform.position, 
                desiredPosition, 
                ref currentVelocity, 
                1.0f / currentCameraSmoothSpeed);
        }
        else
        {
            cameraTransform.position = desiredPosition;
        }
    }
    
    void OnControllerColliderHit(ControllerColliderHit hit)
    {
        if (!enableSlopeStabilization)
            return;
        
        float slopeAngle = Vector3.Angle(hit.normal, Vector3.up);
        if (slopeAngle <= maxSlopeAngle)
        {
            if (moveDirection.y > 0)
            {
                moveDirection.y = Mathf.Min(moveDirection.y, 0.0f);
            }
        }
    }
    
    public void SetMode(CameraMode mode)
    {
        currentMode = mode;
        ApplyModeSettings(mode);
    }
    
    public CameraMode GetCurrentMode()
    {
        return currentMode;
    }
    
    void OnApplicationFocus(bool hasFocus)
    {
        if (hasFocus)
        {
            Cursor.lockState = CursorLockMode.Locked;
            Cursor.visible = false;
        }
        else
        {
            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
        }
    }
}
