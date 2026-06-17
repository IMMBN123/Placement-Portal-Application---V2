const { createApp, ref, reactive, onMounted } = Vue;

const App = {
    setup() {
        const user = ref(null);
        const isLoading = ref(true);
        const isSubmitting = ref(false);
        const alertMessage = ref('');
        const alertType = ref('success')
        const loginForm = reactive({ email: '', password: '' });
        const dashboardData = ref({});
        const allSearchData = ref({}); 
        const isExporting = ref(false);
        const showPassword = ref(false);
        
        // Controls which screen is shown when NOT logged in
        const authView = ref('landing');
        const adminView = ref('main');
        
        const studentForm = reactive({
            email: '', password: '', full_name: '', roll_number: '',
            age: '', branch: '', graduation_year: '', cgpa: '',
            phone: '', linkedin_url: ''
        });

        const studentResumeFile = ref(null);
        
        const companyForm = reactive({
            email: '', password: '', company_name: '', industry: '',
            phone: '', website: '', description: ''
        });

        const handleFileUpload = (event) => {
            studentResumeFile.value = event.target.files[0];
        };

        const checkSession = async () => {
            try {
                const response = await fetch('/api/auth/me');
                if (response.ok) {
                    const data = await response.json();
                    user.value = data.user;
                    if (user.value.role === 'admin') await fetchAdminDashboard();
                    else if (user.value.role === 'student') await fetchStudentDashboard();
                    else await fetchCompanyDashboard();
                } else {
                    user.value = null;
                }
            } catch (error) {
                user.value = null;
            } finally {
                isLoading.value = false;
            }
        };

        let alertTimer=null;

        const showAlert = (message, type = 'success') => {
            alertMessage.value = message;
            alertType.value = type;

            if (alertTimer) {
                clearTimeout(alertTimer);
            }

            alertTimer = setTimeout(() => {
                alertMessage.value = '';
            }, 5000);
        };

        const login = async () => {
            isSubmitting.value = true;
            alertMessage.value = ''; 
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(loginForm)
                });
                const data = await response.json();
                if (response.ok) {
                    user.value = data.user; 
                    loginForm.password = '';
                    if (user.value.role === 'admin') await fetchAdminDashboard(); 
                    else if (user.value.role === 'student') await fetchStudentDashboard(); 
                    else await fetchCompanyDashboard();
                } else {
                    showAlert(data.error || 'Login failed', 'danger');
                }
            } catch (error) {
                showAlert('A network error occured while logging in', 'danger');
            } finally {
                isSubmitting.value = false;
            }
        };

        const logout = async () => {
            try {
                await fetch('/api/auth/logout', { method: 'POST' });
                user.value = null;
                dashboardData.value = {};
                companyDashboardData.value = {}; 
                authView.value = 'landing';
            } catch (error) {
                console.error("Logout error:", error);
                showAlert('Unexpected error! Try again', 'danger');
            }
        };

        const registerStudent = async () => {
            isSubmitting.value = true;
            alertMessage.value = '';

            const formData = new FormData();
            for (const key in studentForm) {
                formData.append(key, studentForm[key]);
            }

            if (studentResumeFile.value) {
                formData.append('resume_link', studentResumeFile.value);
            }

            try {
                const response = await fetch('/api/auth/register/student', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert('Registration successful! Please login now.', 'success')
                    authView.value = 'login';

                    for (let key in studentForm) studentForm[key] = '';
                    studentResumeFile.value = null;
                } else {
                    showAlert( data.error || 'Registration failed.', 'danger');
                }
            } catch (error) {
                console.error(error);
                showAlert("A network error occurred during registration.", 'danger');
            } finally {
                isSubmitting.value = false;
            }
        };

        const registerCompany = async () => {
            isSubmitting.value = true;
            alertMessage.value = '';

            const formData = new FormData();
            for (const key in companyForm) {
                formData.append(key, companyForm[key]);
            }

            try {
                const response = await fetch('/api/auth/register/company', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert('Registration successful! Await admin approval.', 'success')
                    authView.value = 'login';

                    for (let key in companyForm) companyForm[key] = '';
                } else {
                    showAlert( data.error || 'Registration failed.', 'danger');
                }
            } catch (error) {
                console.error(error);
                showAlert("A network error occurred during registration.", 'danger');
            } finally {
                isSubmitting.value = false;
            }
        };

        const fetchAdminDashboard = async () => {
            try {
                const response = await fetch('/api/admin/dashboard');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value = {
                        stats: {
                            students: data.active_students,
                            companies: data.active_companies,
                            drives: data.active_drives,
                            pending_companies: data.pending_companies,
                            pending_drives: data.pending_drives,
                            blacklisted_students: data.blacklisted_students,
                            blacklisted_companies: data.blacklisted_companies
                        }
                    };

                    await getFiveStudents();
                    await getFiveCompanies();
                    await getPendingCompanies();
                    await getFiveDrives();
                    await getPendingDrives();
                }
            } catch (error) {
                showAlert("Failed to load admin dashboard data.", 'danger');
                console.error("Failed to load admin dashboard data.", error);
            }
        };

        const studentColumns = ref([
            {key: 'roll_number', label: 'Roll Number'},
            {key: 'full_name', label: 'Student Name'},
            {key: 'branch', label: 'Department'},
            {key: 'cgpa', label: 'CGPA'}
        ]);

        const companyColumns = ref([
            {key: 'user_id', label: 'Company ID'},
            {key: 'company_name', label: 'Company Name'},
            {key: 'industry', label: 'Industry'},
            {key: 'website', label: 'Website'}
        ]);

        const driveColumns = ref([
            {key: 'id', label: 'Drive ID'},
            {key: 'company_name', label: 'Company'},
            {key: 'job_title', label: 'Role'},
            {key: 'deadline', label: 'Deadline'},
            {key: 'application_count', label: 'Applications'}
        ]);

        const applicationColumns = ref([
            {key: 'placement_drive_id', label: 'Drive ID'},
            {key: 'roll_number', label: 'Student Roll Number'},
            {key: 'company_id', label: 'Company ID'},
            {key: 'company_name', label: 'Company Name'},
            {key: 'applied_at', label: 'Applied On'},
            {key: 'status', label: 'Status'}
        ])

        const getFiveStudents = async () => {
            try {
                const response = await fetch('/api/admin/glance/students');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value.fiveStudents = data.five_students;
                }
            } catch (error) {
                console.error("Failed to fetch students:", error);
            }
        };

        const getAllStudents = async () => {
            try {
                const response = await fetch('/api/admin/students');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value.blacklisted_students = data.blacklisted_students;
                    dashboardData.value.active_students = data.active_students;
                    adminView.value = 'all_students';
                } else {
                    showAlert("Couldn't retrieve students! Try Again.", 'danger');
                }
            } catch (error) {
                console.error("Failed to fetch all students", error);
                showAlert("Network Exception", 'danger');
            }
        }

        const updateStudentForm = reactive({
                    user_id: '', email: '', full_name: '', roll_number: '',
                    branch: '', age: '', graduation_year: '', cgpa: '',
                    phone: '', linkedin_url: ''
                });

        const getStudentData = (student) => {
            updateStudentForm.user_id = student.user_id;
            updateStudentForm.email =  student.email;
            updateStudentForm.full_name = student.full_name;
            updateStudentForm.roll_number = student.roll_number;
            updateStudentForm.branch = student.branch;
            updateStudentForm.age = student.age;
            updateStudentForm.graduation_year = student.graduation_year;
            updateStudentForm.cgpa = student.cgpa;
            updateStudentForm.phone = student.phone;
            updateStudentForm.linkedin_url = student.linkedin_url || '';

            adminView.value = 'update_student'
        };


        const updateStudent = async () => {
            isSubmitting.value = true;
            try {
                const response = await fetch(`/api/admin/student/${updateStudentForm.user_id}/update`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updateStudentForm)
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert(data.message || "Student profile updated successfully!", "success");
                    adminView.value = 'main';
                    await fetchAdminDashboard();
                } else {
                    showAlert(data.error || "Update failed.", "danger");
                }
            } catch (error) {
                showAlert("A network error occurred while submitting student modifications.", "danger");
            } finally {
                isSubmitting.value = false;
            }
        };

        const getFiveCompanies = async () => {
            try {
                const response = await fetch('/api/admin/glance/companies');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value.fiveCompanies = data.five_companies;
                }
            } catch (error) {
                console.error("Failed to fetch companies:", error);
            }
        };

        const getPendingCompanies = async () => {
            try {
                const response = await fetch('/api/admin/pending/companies');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value.pendingCompanies = data.pending_companies;
                }
            } catch (error) {
                console.error("Failed to fetch companies:", error);
            }
        };

        const getAllCompanies = async () => {
            try {
                const response = await fetch('/api/admin/companies');
                if (response.ok) {
                    const data = await response.json();
                    await getPendingCompanies();
                    dashboardData.value.blacklistedCompanies = data.blacklisted_companies;
                    dashboardData.value.activeCompanies = data.active_companies;
                    adminView.value = 'all_companies';
                } else {
                    showAlert("Couldn't retrieve Companies! Try Again.", 'danger');
                }
            } catch (error) {
                console.error("Failed to fetch all companies!", error);
                showAlert("Network Exception while retrieving companies!", 'danger');
            }
        }

        const updateCompanyForm = reactive({
                    user_id: '', email: '', company_name: '', industry: '',
                    website: '', phone: '', description: ''
                });

        const getCompanyData = (company) => {
            updateCompanyForm.user_id = company.user_id;
            updateCompanyForm.email =  company.email;
            updateCompanyForm.company_name = company.company_name;
            updateCompanyForm.industry = company.industry;
            updateCompanyForm.website = company.website;
            updateCompanyForm.phone = company.phone;
            updateCompanyForm.description = company.description;

            if (user.value.role === 'admin') adminView.value = 'update_company';
            if (user.value.role === 'company') companyView.value = 'update_profile';
        };


        const updateCompany = async () => {
            isSubmitting.value = true;
            try {
                const response = await fetch(`/api/admin/company/${updateCompanyForm.user_id}/update`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updateCompanyForm)
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert(data.message || "Company profile updated successfully!", "success");
                    adminView.value = 'main';
                    await fetchAdminDashboard();
                } else {
                    showAlert(data.error || "Update failed.", "danger");
                }
            } catch (error) {
                showAlert("A network error occurred while submitting Company modifications.", "danger");
            } finally {
                isSubmitting.value = false;
            }
        };

        const getFiveDrives = async () => {
            try {
                const response = await fetch('/api/admin/glance/drives');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value.fiveDrives = data.five_drives;
                    await fetchApplicationCounts(dashboardData.value.fiveDrives);
                }
            } catch (error) {
                console.error("Failed to fetch drives:", error);
            }
        };

        const getPendingDrives = async () => {
            try {
                const response = await fetch('/api/admin/pending/drives');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value.pendingDrives = data.pending_drives;
                }
            } catch (error) {
                console.error("Failed to fetch drives:", error);
            }
        };

        const getAllDrives = async () => {
            try {
                const response = await fetch('/api/admin/drives');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value.ongoingDrives = data.ongoing_drives;
                    dashboardData.value.closedDrives = data.closed_drives;
                    dashboardData.value.drives_by_blacklisted_companies = data.drives_by_blacklisted_companies;

                    await fetchApplicationCounts(dashboardData.value.ongoingDrives);
                    await fetchApplicationCounts(dashboardData.value.closedDrives);
                    await fetchApplicationCounts(dashboardData.value.drives_by_blacklisted_companies);

                    adminView.value = 'all_drives'
                }
            } catch (error) {
                console.error("Failed to fetch drives:", error);
            }
        };

        const getFiveApplications = async () => {
            try {
                const response = await fetch('/api/admin/glance/applications');
                if (response.ok) {
                    const data = await response.json();
                    dashboardData.value.fiveApplications = data.five_applications;
                }
            } catch (error) {
                console.error("Failed to fetch applications:", error);
            }
        };

        const search_term = ref('');

        const getAllSearch = async () => {
            isSubmitting.value = true;

            try {
                const response = await fetch(`api/admin/search/all?q=${encodeURIComponent(search_term.value.trim())}`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();

                if (response.ok) {
                    adminView.value = 'all_search';
                    allSearchData.value.active_students = data.active_students;
                    allSearchData.value.blacklisted_students = data.blacklisted_students;
                    allSearchData.value.active_companies = data.active_companies;
                    allSearchData.value.pending_companies = data.pending_companies;
                    allSearchData.value.blacklisted_companies = data.blacklisted_companies;
                    allSearchData.value.ongoing_drives = data.ongoing_drives;
                    allSearchData.value.closed_drives = data.closed_drives;
                    allSearchData.value.drives_by_blacklisted_companies = data.drives_by_blacklisted_companies;
                    allSearchData.value.pending_drives = data.pending_drives;
                    allSearchData.value.current_applications = data.current_applications
                    allSearchData.value.applications_for_closed_drives = data.applications_for_closed_drives
                    allSearchData.value.applications_for_blacklisted_companies = data.applications_for_blacklisted_companies
                    allSearchData.value.applications_by_blacklisted_students = data.applications_by_blacklisted_students
                }
                else {
                    adminView.value = 'main'
                    showAlert(data.error || "Something unexpected happened. Please try again", 'danger');
                }
            } catch (error) {
                console.error("Search error:", error);
                showAlert("A network error occurred while updating status.", "danger");
            } finally {
                isSubmitting.value = false;
            } 
        };

        const toggleBlacklist = async (userItem) => {
            isSubmitting.value = true;
            
            // Fallback logic to check if your row key is named 'user_id' or standard 'id'
            const targetId = userItem.user_id;
            
            try {
                const response = await fetch(`/api/admin/user/${targetId}/blacklist`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert(data.message, 'success');
                } else {
                    showAlert(data.error || "Failed to change blacklist status.", "danger");
                }
            } catch (error) {
                console.error("Blacklist toggle error:", error);
                showAlert("A network error occurred while updating status.", "danger");
            } finally {
                isSubmitting.value = false;
                await fetchAdminDashboard();
                if (adminView.value == 'all_search'){await getAllSearch();}
                if (adminView.value == 'all_students'){await getAllStudents();}
                if (adminView.value == 'all_companies'){await getAllCompanies();}
            }
        };

        const showConfirmModal = ref(false);
        const activeModalItem = ref(null);

        const openConfirmModal = (userItem) => {
            activeModalItem.value = userItem;
            showConfirmModal.value = true;
        };

        const deleteUser = async (userItem) => {
            isSubmitting.value = true;
            
            // Fallback logic to check if your row key is named 'user_id' or standard 'id'
            const targetId = userItem.user_id;
            
            try {
                const response = await fetch(`/api/admin/user/${targetId}/delete`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert(data.message, 'success');
                } else {
                    showAlert(data.error || "Failed to deactivate user.", "danger");
                }
            } catch (error) {
                console.error("Deactivation error:", error);
                showAlert("A network error occurred while deactivating user.", "danger");
            } finally {
                isSubmitting.value = false;
                await fetchAdminDashboard();
                if (adminView.value == 'all_search'){await getAllSearch();}
                if (adminView.value == 'all_students'){await getAllStudents();}
                if (adminView.value == 'all_companies'){await getAllCompanies();}
            }
        };

        const executeModalAction = async () => {
            showConfirmModal.value = false; // Hide the popup instantly
            
            if (activeModalItem.value) {
                // Run the master toggleBlacklist routine passing our safely cached item reference
                await deleteUser(activeModalItem.value);
                activeModalItem.value = null; // Flush cache allocation space clean
            }
        };

        const approveCompany = async (company) => {
            isSubmitting.value = true;
            alertMessage.value = '';
            
            try {
                // Use backticks (``) to pass the company ID straight through the URL path
                const response = await fetch(`/api/admin/companies/${company.user_id}/approve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showAlert( data.message || 'Company approved successfully', 'success');

                } else {
                    showAlert( data.error || 'Failed to process approval', 'danger');
                }
            } catch (error) {
                console.error("Network error processing approval:", error);
                showAlert( data.error || 'A netwrok error occured.', 'danger');
            } finally {
                isSubmitting.value = false;
                await fetchAdminDashboard();
                if (adminView.value == 'all_search'){await getAllSearch();}
                if (adminView.value == 'all_companies'){await getAllCompanies();}
            }
        };

        const rejectCompany = async (company) => {
            isSubmitting.value = true;
            alertMessage.value = '';
            
            try {
                const response = await fetch(`/api/admin/companies/${company.user_id}/reject`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showAlert( data.message || 'Company rejected successfully', 'success');

                } else {
                    showAlert( data.error || 'Failed to process rejection', 'danger');
                }
            } catch (error) {
                console.error("Network error processing rejection:", error);
                showAlert( data.error || 'A netwrok error occured.', 'danger');
            } finally {
                isSubmitting.value = false;
                await fetchAdminDashboard();
                if (adminView.value == 'all_search'){await getAllSearch();}
                if (adminView.value == 'all_companies'){await getAllCompanies();}
            }
        };

        const approveDrive = async (drive) => {
            isSubmitting.value = true;
            alertMessage.value = '';
            
            try {
                const response = await fetch(`/api/admin/drives/${drive.id}/approve`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showAlert( data.message || 'Drive approved successfully', 'success');

                } else {
                    showAlert( data.error || 'Failed to process approval', 'danger');
                }
            } catch (error) {
                console.error("Network error processing approval:", error);
                showAlert( data.error || 'A netwrok error occured.', 'danger');
            } finally {
                isSubmitting.value = false;
                await fetchAdminDashboard();
                if (adminView.value == 'all_search'){await getAllSearch();}
            }
        };

        const rejectDrive = async (drive) => {
            isSubmitting.value = true;
            alertMessage.value = '';
            
            try {
                const response = await fetch(`/api/admin/drives/${drive.id}/reject`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                const data = await response.json();
                
                if (response.ok) {
                    showAlert( data.message || 'Drive rejected successfully', 'success');

                } else {
                    showAlert( data.error || 'Failed to process rejection', 'danger');
                }
            } catch (error) {
                console.error("Network error processing rejection:", error);
                showAlert( data.error || 'A netwrok error occured.', 'danger');
            } finally {
                isSubmitting.value = false;
                await fetchAdminDashboard();
                if (adminView.value == 'all_search'){await getAllSearch();}
            }
        };

        const companyView = ref('main')
        const companyDashboardData = ref({})
        const driveForm = reactive({
            job_title: '', min_cgpa: '', package_lpa: '', vacancies: '', location: '',
            deadline: '', job_description: ''
        })

        const companyDriveColumns = ref([
            {key: 'id', label: 'Drive ID'},
            {key: 'job_title', label: 'Role'},
            {key: 'package_lpa', label: 'Package (LPA)'},
            {key: 'deadline', label: 'Deadline'},
            {key: 'application_count', label: 'Applicants'}
        ]);

        const fetchCompanyDashboard = async () => {
            try {
                const response = await fetch('/api/company/dashboard');
                if (response.ok) {
                    const data = await response.json();
                    companyDashboardData.value = {
                        stats: {
                            active_drives: data.active_drives,
                            closed_drives: data.closed_drives,
                            pending_drives: data.pending_drives,
                            rejected_drives: data.rejected_drives,
                            new_applications: data.new_applications,
                            shortlisted_applications: data.shortlisted_applications,
                            accepted_applications: data.accepted_applications,
                            rejected_applications: data.rejected_applications
                        }
                    };
                    await getDrives();
                }
            } catch (error) {
                showAlert("Failed to load company dashboard data.", 'danger');
                console.error("Failed to load company dashboard data.", error);
            }
        };

        const createDrive = async () => {
            isSubmitting.value = true;
            const formData = new FormData();
            for (const key in driveForm) {
                formData.append(key, driveForm[key]);
            }
            try {
                const response = await fetch('/api/company/create-drive', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (response.ok) {
                    companyView.value = 'main';
                    showAlert(data.message, 'success');
                } else {
                    showAlert(data.error, 'danger');
                }
            } catch(error){
                console.error("Error while creating drive:", error);
                showAlert("Unexpected network error occured!", 'danger');
            } finally {
                isSubmitting.value = false;
                await fetchCompanyDashboard();
            }
        }

        const getDrives = async() => {
            try{
                const response = await fetch('/api/company/drives');
                if (response.ok) {
                    const data = await response.json()
                    companyDashboardData.value.ongoingDrives = data.ongoing_drives;
                    companyDashboardData.value.pendingDrives = data.pending_drives;
                    companyDashboardData.value.closedDrives = data.closed_drives;
                    companyDashboardData.value.rejectedDrives = data.rejected_drives

                    await fetchApplicationCounts(companyDashboardData.value.ongoingDrives);
                    await fetchApplicationCounts(companyDashboardData.value.pendingDrives);
                    await fetchApplicationCounts(companyDashboardData.value.closedDrives);
                    await fetchApplicationCounts(companyDashboardData.value.rejectedDrives);
                }
            } catch (error) {
                console.error('Error while retrieving drives:',error);
                showAlert("Something unexpected happened!", 'danger')
            }
        }

        const fetchApplicationCounts = async (drivesList) => {
            if (!drivesList || drivesList.length === 0) return;
            for (let drive of drivesList) {
                try {
                    const response = await fetch(`/api/company/drives/${drive.id}/app-count`);
                    if (response.ok) {
                        const data = await response.json(); 
                        drive.application_count = data.count || 0; 
                    } else {
                        drive.application_count = 0;
                    }
                } catch (error) {
                    console.error(`Error fetching applications count for drive ${drive.id}:`, error);
                    drive.application_count = 0;
                }
            }
        };

        const companyProfile = reactive({
            user_id: '',
            email: '',
            company_name: '',
            industry: '',
            description: '',
            website: '',
            phone: '',
            is_approved: false
        });

        const getCompanyProfile = async() => {
            isSubmitting.value = true;
            try {
                const response = await fetch('/api/company/profile');
                const data = await response.json();
                if (response.ok) {
                    companyView.value = 'profile';
                    companyProfile.user_id = data.user_id;
                    companyProfile.email = data.email;
                    companyProfile.company_name = data.company_name;
                    companyProfile.industry = data.industry;
                    companyProfile.website = data.website;
                    companyProfile.phone = data.phone;
                    companyProfile.description = data.description;
                    companyProfile.is_approved = data.is_approved;
                } else {
                    showAlert(data.error || "Failed to load company profile.", 'danger');
                }
            } catch(error) {
                console.error("Error while fetching profile:",error);
                showAlert("Something unexpected happened! Try again", 'danger');
            } finally {
                isSubmitting.value = false;
            }
        };

        const selfUpdateCompany = async () => {
            isSubmitting.value = true;
            try {
                const response = await fetch('/api/company/update', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updateCompanyForm)
                });

                const data = await response.json();

                if (response.ok) {
                    showAlert(data.message || "Company profile updated successfully!", "success");
                    companyView.value = 'profile';
                    await getCompanyProfile();
                } else {
                    showAlert(data.error || "Update failed.", "danger");
                }
            } catch (error) {
                console.error("Error while updating:",error)
                showAlert("A network error occurred while submitting Company modifications.", "danger");
            } finally {
                isSubmitting.value = false;
            }
        };

        const closeDrive = async(drive) => {
            isSubmitting.value = true;
            try {
                const response = await fetch(`api/company/drives/${drive.id}/close`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                });
                const data = await response.json();
                if (response.ok) {
                    showAlert(data.message, 'success');
                } else
                    showAlert(data.error, 'danger');
            } catch(error) {
                console.error("Error while closing drive:", error);
                showAlert("A network exception occured! Try again", "danger")
            } finally {
                isSubmitting.value = false;
                if (user.value.role == 'admin') {
                    if (adminView.value == 'main') await fetchAdminDashboard();
                    if (adminView.value == 'all_search') await getAllSearch();
                    if (adminView.value == 'all_drives') await getAllDrives();
                } else {
                    await fetchCompanyDashboard();
                }
            }
        };

        const driveDetails = reactive({id: '', company_name: '', job_title: '', job_description: '', package_lpa: '',
            vacancies: '', min_cgpa: '', deadline: '', created_at: ''
        })

        const viewDrive = async(drive) => {
            if (user.value.role == 'admin') adminView.value = 'view_drive';
            if (user.value.role == 'company') companyView.value = 'view_drive';
            driveDetails.id = drive.id;
            driveDetails.company_name = drive.company_name;
            driveDetails.job_title = drive.job_title;
            driveDetails.job_description = drive.job_description;
            driveDetails.package_lpa = drive.package_lpa;
            driveDetails.vacancies = drive.vacancies;
            driveDetails.min_cgpa = drive.min_cgpa;
            driveDetails.deadline = drive.deadline;
            driveDetails.created_at = drive.created_at;
        }

        const getApplications = async(drive) => {
            try {
                const response = await fetch(`/api/company/drives/${drive.id}/applications`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' },
                });
                const data = await response.json();
                if (response.ok) {
                    if (user.value.role == 'company') {
                        companyDashboardData.value.new_applications = data.new_applications;
                        companyDashboardData.value.accepted_applications = data.accepted_applications;
                        companyDashboardData.value.shortlisted_applications = data.shortlisted_applications;
                        companyDashboardData.value.rejected_applications = data.rejected_applications;
                    }
                    if (user.value.role == 'admin') {
                        dashboardData.value.new_applications = data.new_applications;
                        dashboardData.value.accepted_applications = data.accepted_applications;
                        dashboardData.value.shortlisted_applications = data.shortlisted_applications;
                    }
                    await viewDrive(drive);
                } else {
                    showAlert("Couldn't fetch student applications", 'danger');
                }
            } catch(error) {
                console.error('Error while fetching applications:', error);
                showAlert("Unexpected behaviour encountered.", 'danger')
            }
        };
            
        const fetchStudentDashboard = async () => {
            dashboardData.value = {
                drives: [
                    { id: 1, title: 'Software Engineer', company_id: 101 },
                    { id: 2, title: 'Data Analyst', company_id: 204 }
                ]
            };
        };

        const triggerExport = async () => {
            isExporting.value = true;
            setTimeout(() => {
                isExporting.value = false;
                alertMessage.value = "Export complete (Mocked)!";
            }, 2000);
        };

        onMounted(() => {
            checkSession();
        });

        return {
            user, isLoading, isSubmitting, alertMessage, loginForm,
            dashboardData, isExporting, triggerExport, showPassword, login, logout,
            authView, studentForm, handleFileUpload, registerStudent,
            companyForm, registerCompany, studentColumns, companyColumns,
            getFiveStudents, getFiveCompanies, getPendingCompanies, adminView,
            getFiveDrives, driveColumns, getPendingDrives, applicationColumns, 
            getFiveApplications, approveCompany, rejectCompany, alertTimer, alertType,
            showAlert, approveDrive, rejectDrive, toggleBlacklist, deleteUser,
            showConfirmModal, activeModalItem, openConfirmModal, executeModalAction,
            updateStudentForm, getStudentData, updateStudent, updateCompanyForm,
            getCompanyData, updateCompany, allSearchData, search_term, getAllSearch,
            getAllStudents, getAllCompanies, companyView, companyDashboardData,
            fetchCompanyDashboard, driveForm, createDrive, companyProfile, getCompanyProfile,
            selfUpdateCompany, closeDrive, companyDriveColumns, getApplications, driveDetails,
            getAllDrives, fetchApplicationCounts, viewDrive
        };
    }
};

document.addEventListener('DOMContentLoaded', () => {
    const app = createApp(App);

    app.component('dashboard-table', {
    props: ['title', 'columns', 'items'],
    template: `
        <div class="card">
            <div class="card-header bg-white d-flex justify-content-between align-items-center py-3">
                <h5 class="mb-0" style="color: #3c6e71; font-weight: bold;">{{ title }}</h5>
                <slot name="view-all" :row="item"></slot>
            </div>
            
            <div class="card-body p-0">
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th v-for="col in columns" :key="col.key">{{ col.label }}</th>
                                <th style="display: flex; justify-content: center; gap: 5px;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="item in items" :key="item.id">
                                <td v-for="col in columns" :key="col.key">{{ item[col.key] }}</td>
                                <td>
                                    <slot name="table-actions" :row="item"></slot>
                                </td>
                            </tr>
                            <tr v-if="!items || items.length === 0">
                                <td :colspan="columns.length + 1" class="text-center py-4 text-muted">No data available</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `
    });

    app.component('view-drive',{
    props:['drive','data'],
    template: `
        <div class="card border-0 rounded-3 bg-white p-4 p-md-5">
                            <div class="d-flex flex-column flex-md-row justify-content-between align-items-start gap-3 border-bottom pb-4 mb-4">
                                <div>
                                    <span class="badge bg-light text-primary border border-primary-subtle rounded-pill mb-2 px-3 py-1.5 small fw-semibold">
                                        <i class="bi bi-briefcase-fill me-1"></i> Placement Drive
                                    </span>
                                    <h1 class="h2 fw-bold text-dark mb-1">{{ drive.job_title }}</h1>
                                    <p class="text-secondary fs-5 mb-0 d-flex align-items-center gap-2">
                                        <i class="bi bi-building text-muted"></i>
                                        <strong>{{ drive.company_name }}</strong>
                                    </p>
                                </div>
                                
                                <div class="text-md-end">
                                    <span v-if="data.fiveDrives?.some(d => d.id === drive.id)" class="badge bg-success-subtle text-success border border-success-subtle px-3 py-2 rounded-pill small fw-semibold">
                                        Active Drive
                                    </span>
                                    <span v-else-if="data.ongoingDrives?.some(d => d.id === drive.id)" class="badge bg-success-subtle text-success border border-success-subtle px-3 py-2 rounded-pill small fw-semibold">
                                        Active Drive
                                    </span>
                                    <span v-else-if="data.pendingDrives?.some(d => d.id === drive.id)" class="badge bg-warning-subtle text-warning border border-warning-subtle px-3 py-2 rounded-pill small fw-semibold">
                                        Pending Drive
                                    </span>
                                    <span v-else-if="data.closedDrives?.some(d => d.id === drive.id)" class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-3 py-2 rounded-pill small fw-semibold">
                                        Closed Drive
                                    </span>
                                    <span v-else-if="data.rejectedDrives?.some(d => d.id === drive.id)" class="badge bg-danger-subtle text-danger border border-danger-subtle px-3 py-2 rounded-pill small fw-semibold">
                                        Rejected Drive
                                    </span>
                                </div>
                            </div>

                            <div class="row g-3 mb-4">
                                <div class="col-6 col-md-3">
                                    <div class="card bg-light border-0 h-100 rounded-3 p-3">
                                        <span class="d-block text-muted text-uppercase fw-semibold mb-1" style="font-size: 0.75rem;">Compensation</span>
                                        <h5 class="fw-bold text-dark mb-0 d-flex align-items-center gap-1">
                                            <span>{{ drive.package_lpa }}</span>
                                            <span class="text-muted small fs-6">LPA</span>
                                        </h5>
                                    </div>
                                </div>

                                <div class="col-6 col-md-3">
                                    <div class="card bg-light border-0 h-100 rounded-3 p-3">
                                        <span class="d-block text-muted text-uppercase fw-semibold mb-1" style="font-size: 0.75rem;">Vacancies</span>
                                        <h5 class="fw-bold text-dark mb-0">{{ drive.vacancies }} Openings</h5>
                                    </div>
                                </div>

                                <div class="col-6 col-md-3">
                                    <div class="card bg-light border-0 h-100 rounded-3 p-3">
                                        <span class="d-block text-muted text-uppercase fw-semibold mb-1" style="font-size: 0.75rem;">Cut-off CGPA</span>
                                        <h5 class="fw-bold text-danger mb-0">≥ {{ drive.min_cgpa }}</h5>
                                    </div>
                                </div>

                                <div class="col-6 col-md-3">
                                    <div class="card bg-light border-0 h-100 rounded-3 p-3">
                                        <span class="d-block text-muted text-uppercase fw-semibold mb-1" style="font-size: 0.75rem;">Apply Before</span>
                                        <h5 class="fw-bold text-warning-emphasis mb-0 d-flex align-items-center gap-1.5" style="font-size: 0.95rem; gap: 10px;">
                                            <i class="bi bi-clock-history text-warning"></i>
                                            <span>{{ drive.deadline }}</span>
                                        </h5>
                                    </div>
                                </div>
                            </div>

                            <div class="mb-4">
                                <h4 class="h6 fw-bold text-uppercase text-muted tracking-wider mb-3">
                                    <i class="bi bi-file-text me-1"></i> Job Description & Requirements
                                </h4>
                                <div class="bg-light p-4 rounded-3 border-0 text-secondary lh-lg fs-6" style="white-space: pre-line;">
                                    {{ drive.job_description }}
                                </div>
                            </div>

                            <div class="border-top pt-4 mt-4 d-flex flex-wrap justify-content-between align-items-center gap-3 text-muted" style="font-size: 0.8rem;">
                                <div>
                                    <span>Drive ID: </span>
                                    <strong class="text-dark bg-light px-2 py-1 rounded">{{ drive.id }}</strong>
                                </div>
                                <div>
                                    <i class="bi bi-calendar3 me-1"></i> Posted on: <strong>{{ drive.created_at }}</strong>
                                </div>
                            </div>

                        </div>
    `
    });

    app.mount('#app');
});