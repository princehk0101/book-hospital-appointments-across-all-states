(() => {
    const form = document.getElementById('bookingForm');
    if (!form) return;

    const district = document.getElementById('districtSelect');
    const hospital = document.getElementById('hospitalSelect');
    const department = document.getElementById('departmentSelect');
    const doctor = document.getElementById('doctorSelect');
    const date = document.getElementById('dateSelect');
    const time = document.getElementById('timeSelect');
    const summary = document.getElementById('bookingSummary');
    const submit = document.getElementById('confirmBooking');

    function reset(select, message) {
        select.replaceChildren(new Option(message, ''));
        select.disabled = true;
    }

    async function load(select, url, params, emptyMessage) {
        reset(select, 'Loading…');
        try {
            const query = new URLSearchParams(params);
            const response = await fetch(`${url}?${query}`, { headers: { 'Accept': 'application/json' } });
            if (!response.ok) throw new Error('Could not load options');
            const data = await response.json();
            select.replaceChildren(new Option(data.results.length ? 'Choose an option' : emptyMessage, ''));
            data.results.forEach(item => select.add(new Option(item.name, item.id)));
            select.disabled = data.results.length === 0;
        } catch (_error) {
            reset(select, 'Could not load options. Please try again.');
        }
    }

    function updateSummary() {
        const chosen = [district, hospital, department, doctor, date, time].every(el => el.value);
        submit.disabled = !chosen;
        if (!chosen) {
            summary.textContent = 'Select a district, hospital, department, doctor, date and time to review your booking.';
            return;
        }
        const values = [district, hospital, department, doctor, date, time].map(el => el.selectedOptions[0]?.text || el.value);
        summary.textContent = `Booking summary\n${values.map((v, i) => `${['District', 'Hospital', 'Department', 'Doctor', 'Date', 'Time'][i]}: ${v}`).join('\n')}`;
    }

    district.addEventListener('change', () => {
        reset(hospital, 'Select district first'); reset(department, 'Select hospital first'); reset(doctor, 'Select department first');
        if (district.value) load(hospital, form.dataset.hospitalsUrl, { district: district.value }, 'No hospitals found in this district').then(updateSummary);
        updateSummary();
    });
    hospital.addEventListener('change', () => {
        reset(department, 'Loading…'); reset(doctor, 'Select department first');
        if (hospital.value) load(department, form.dataset.departmentsUrl, { hospital: hospital.value }, 'No departments found at this hospital').then(updateSummary);
        updateSummary();
    });
    department.addEventListener('change', () => {
        reset(doctor, 'Loading…');
        if (department.value) load(doctor, form.dataset.doctorsUrl, { hospital: hospital.value, department: department.value }, 'No doctors found in this department').then(updateSummary);
        updateSummary();
    });
    [doctor, date, time].forEach(el => el.addEventListener('change', updateSummary));
    form.addEventListener('submit', event => {
        if (!form.reportValidity() || submit.disabled) event.preventDefault();
    });
    updateSummary();
})();
