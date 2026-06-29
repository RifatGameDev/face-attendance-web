const API_BASE_URL = "https://wages-wasabi-coasting.ngrok-free.dev";

//const API_BASE_URL = "";

const landingPage = document.getElementById("landingPage");
const verifyPage = document.getElementById("verifyPage");
const registerPage = document.getElementById("registerPage");

const verifyVideo = document.getElementById("verifyVideo");
const registerVideo = document.getElementById("registerVideo");
const captureCanvas = document.getElementById("captureCanvas");
const verifyCameraCircle = document.getElementById("verifyCameraCircle");

const verifyMessage = document.getElementById("verifyMessage");
const verifyLoader = document.getElementById("verifyLoader");
const verifyResult = document.getElementById("verifyResult");
const verifyRegisterBtn = document.getElementById("verifyRegisterBtn");
const verifyActionButtons = document.getElementById("verifyActionButtons");

const registerStartBox = document.getElementById("registerStartBox");
const captureBox = document.getElementById("captureBox");
const nameSubmitBox = document.getElementById("nameSubmitBox");
const registerStepMessage = document.getElementById("registerStepMessage");
const captureCounter = document.getElementById("captureCounter");
const progressRingCircle = document.getElementById("progressRingCircle");
const registrationResult = document.getElementById("registrationResult");
const verifyYourselfBtn = document.getElementById("verifyYourselfBtn");

let activeStream = null;
let capturedImages = {
    FRONT: null,
    LEFT: null,
    RIGHT: null
};

const CAPTURE_STEPS = [
    {
        pose: "FRONT",
        message: "Show your front face. Please hold for 3 seconds."
    },
    {
        pose: "LEFT",
        message: "Turn your face to the left. Please hold for 3 seconds."
    },
    {
        pose: "RIGHT",
        message: "Turn your face to the right. Please hold for 3 seconds."
    }
];

function showScreen(screen) {
    landingPage.classList.remove("active");
    verifyPage.classList.remove("active");
    registerPage.classList.remove("active");

    screen.classList.add("active");
}

function goToLandingPage() {
    stopCamera();
    showScreen(landingPage);
}

function goToRegisterPage() {
    stopCamera();
    resetRegisterUI();
    showScreen(registerPage);
}

async function goToVerifyPage() {
    stopCamera();
    resetVerifyUI();
    showScreen(verifyPage);
    await startVerifyFlow();
}

async function retryVerification() {
    stopCamera();
    resetVerifyUI();
    await startVerifyFlow();
}

async function startCamera(videoElement) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Camera is not available. Please use HTTPS and a supported browser.");
    }

    activeStream = await navigator.mediaDevices.getUserMedia({
        video: {
            facingMode: "user",
            width: { ideal: 720 },
            height: { ideal: 1280 }
        },
        audio: false
    });

    videoElement.srcObject = activeStream;

    await new Promise((resolve) => {
        videoElement.onloadedmetadata = () => {
            videoElement.play();
            resolve();
        };
    });
}

function stopCamera() {
    if (activeStream) {
        activeStream.getTracks().forEach(track => track.stop());
        activeStream = null;
    }

    verifyVideo.srcObject = null;
    registerVideo.srcObject = null;
}

function resetVerifyUI() {
    verifyCameraCircle.classList.remove("hidden");

    verifyMessage.classList.remove("hidden");
    verifyMessage.innerText = "Opening camera...";

    verifyLoader.classList.add("hidden");

    verifyResult.classList.add("hidden");
    verifyResult.className = "result-box hidden";
    verifyResult.innerHTML = "";

    verifyActionButtons.classList.add("hidden");
}

function resetRegisterUI() {
    capturedImages = {
        FRONT: null,
        LEFT: null,
        RIGHT: null
    };

    registerStartBox.classList.remove("hidden");
    captureBox.classList.add("hidden");
    nameSubmitBox.classList.add("hidden");
    registrationResult.classList.add("hidden");
    registrationResult.className = "result-box hidden";
    registrationResult.innerHTML = "";
    verifyYourselfBtn.classList.add("hidden");
    document.getElementById("nameInput").value = "";
    setProgress(0);
}

async function startVerifyFlow() {
    try {
        await startCamera(verifyVideo);

        verifyMessage.innerText = "Please look at the camera. Verification will start automatically.";
        verifyLoader.classList.remove("hidden");

        await wait(1600);

        const imageBlob = await captureFromVideo(verifyVideo);
        const capturedImageUrl = URL.createObjectURL(imageBlob);

        verifyMessage.innerText = "Checking your face...";

        const formData = new FormData();
        formData.append("image", imageBlob, "verify_face.jpg");

        const response = await fetch(`${API_BASE_URL}/identify-face`, {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        verifyLoader.classList.add("hidden");
        verifyResult.classList.remove("hidden");

        if (!response.ok) {
            throw new Error(data.detail || "Verification failed.");
        }

        if (data.matched) {
            stopCamera();

            verifyCameraCircle.classList.add("hidden");
            verifyMessage.classList.add("hidden");

            verifyResult.classList.add("success");
            verifyResult.innerHTML = `
        <img src="${capturedImageUrl}" class="verified-image" alt="Verified user image" />

        <div class="confirmation-title">
            ${data.message}
        </div>

        <div class="confirmation-details">
            <strong>Employee ID:</strong> ${data.employee.employee_id}
            <br>
            <strong>Name:</strong> ${data.employee.name}
            <br>
            <strong>Match Score:</strong> ${data.score}
        </div>
    `;

            verifyActionButtons.classList.add("hidden");
        } else {
            verifyResult.classList.add("failed");
            verifyResult.innerHTML = `
                <strong>${data.message}</strong>
                <br><br>
                Match Score: ${data.score ?? "N/A"}
            `;
            verifyMessage.innerText = "Verification failed.";
            verifyActionButtons.classList.remove("hidden");
        }

        stopCamera();

    } catch (error) {
        verifyLoader.classList.add("hidden");
        verifyResult.classList.remove("hidden");
        verifyResult.classList.add("failed");
        verifyResult.innerHTML = `<strong>${error.message}</strong>`;
        verifyMessage.innerText = "Verification failed.";
        verifyActionButtons.classList.remove("hidden");
        stopCamera();
    }
}

async function startRegistrationFlow() {
    try {
        resetRegisterUI();

        registerStartBox.classList.add("hidden");
        captureBox.classList.remove("hidden");

        await startCamera(registerVideo);

        for (let i = 0; i < CAPTURE_STEPS.length; i++) {
            const step = CAPTURE_STEPS[i];

            registerStepMessage.className = "instruction-text";
            registerStepMessage.innerText = step.message;
            captureCounter.innerText = `Step ${i + 1} of 3: ${step.pose}`;

            setProgress(0);

            await wait(600);

            await runThreeSecondProgress();

            registerStepMessage.innerText = `Capturing ${step.pose} face...`;

            const imageBlob = await captureFromVideo(registerVideo);
            capturedImages[step.pose] = imageBlob;

            registerStepMessage.className = "instruction-text capture-success";
            registerStepMessage.innerText = `✓ ${step.pose} face captured successfully.`;

            setProgress(1);

            await wait(1400);

            setProgress(0);

            if (i < CAPTURE_STEPS.length - 1) {
                const nextStep = CAPTURE_STEPS[i + 1];
                registerStepMessage.className = "instruction-text";
                registerStepMessage.innerText = `Get ready for ${nextStep.pose} face capture.`;
                await wait(1000);
            }
        }

        stopCamera();

        captureBox.classList.add("hidden");
        nameSubmitBox.classList.remove("hidden");

    } catch (error) {
        stopCamera();
        captureBox.classList.add("hidden");
        registerStartBox.classList.remove("hidden");
        alert(error.message);
    }
}

async function submitRegistration() {
    const name = document.getElementById("nameInput").value.trim();

    if (!name) {
        alert("Please enter your name.");
        return;
    }

    if (!capturedImages.FRONT || !capturedImages.LEFT || !capturedImages.RIGHT) {
        alert("All 3 face images are required.");
        return;
    }

    registrationResult.classList.remove("hidden");
    registrationResult.className = "result-box";
    registrationResult.innerHTML = "Creating user and registering face. Please wait...";

    try {
        const userFormData = new FormData();
        userFormData.append("name", name);

        const userResponse = await fetch(`${API_BASE_URL}/register-user`, {
            method: "POST",
            body: userFormData
        });

        const userData = await userResponse.json();

        if (!userResponse.ok) {
            throw new Error(userData.detail || "User creation failed.");
        }

        const employeeId = userData.employee.employee_id;

        await uploadFacePose(employeeId, "FRONT", capturedImages.FRONT);
        await uploadFacePose(employeeId, "LEFT", capturedImages.LEFT);
        await uploadFacePose(employeeId, "RIGHT", capturedImages.RIGHT);

        registrationResult.classList.add("success");
        registrationResult.innerHTML = `
            <strong>Registration completed successfully. Now verify yourself.</strong>
            <br><br>
            Name: ${name}
            <br>
            Employee ID: ${employeeId}
        `;

        verifyYourselfBtn.classList.remove("hidden");

    } catch (error) {
        registrationResult.classList.add("failed");
        registrationResult.innerHTML = `<strong>${error.message}</strong>`;
    }
}

async function uploadFacePose(employeeId, pose, imageBlob) {
    const formData = new FormData();
    formData.append("employee_id", employeeId);
    formData.append("pose", pose);
    formData.append("image", imageBlob, `${pose.toLowerCase()}_face.jpg`);

    const response = await fetch(`${API_BASE_URL}/register-face-pose`, {
        method: "POST",
        body: formData
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || `${pose} face registration failed.`);
    }

    return data;
}

function captureFromVideo(videoElement) {
    return new Promise((resolve, reject) => {
        const width = videoElement.videoWidth;
        const height = videoElement.videoHeight;

        if (!width || !height) {
            reject(new Error("Camera is not ready yet."));
            return;
        }

        captureCanvas.width = width;
        captureCanvas.height = height;

        const context = captureCanvas.getContext("2d");
        context.drawImage(videoElement, 0, 0, width, height);

        captureCanvas.toBlob((blob) => {
            if (!blob) {
                reject(new Error("Image capture failed."));
                return;
            }

            resolve(blob);
        }, "image/jpeg", 0.9);
    });
}

function runThreeSecondProgress() {
    return new Promise((resolve) => {
        const duration = 3000;
        const startTime = performance.now();

        function animate(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            setProgress(progress);

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                resolve();
            }
        }

        requestAnimationFrame(animate);
    });
}

function setProgress(progress) {
    const circumference = progressRingCircle.getTotalLength();
    const offset = circumference - progress * circumference;

    progressRingCircle.style.strokeDasharray = `${circumference}`;
    progressRingCircle.style.strokeDashoffset = `${offset}`;
}

function wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}