<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    <title>Document</title>
</head>
<body>
    <button class="btn btn-primary" id="myButton">Hitung K-means</button>
    <div id="kmeans-result"></div>
    <h3>Data hasil scrapping: </h3>
    <table class="table">
    <thead>
        <tr>
            <th scope="col">#</th>
            <th scope="col">Nama</th>
            <th scope="col">Skills</th>
            <th scope="col">Pendidikan</th>
            <th scope="col">Pengalaman</th>
        </tr>
    </thead>
    <tbody id="table-data">

    </tbody>
    </table>
    
<script src="//cdnjs.cloudflare.com/ajax/libs/seedrandom/3.0.5/seedrandom.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
<script src="https://code.jquery.com/jquery-3.7.1.min.js" integrity="sha256-/JqT3SQfawRcv/BIHPThkBvs0OEvtFFmqPF/lYI/Cxo=" crossorigin="anonymous"></script>

<script>

    const pendidikan_list = ["bachelor", "ph.d", "master", "magister", "doctor", "s.", "diploma", "sarjana", "associate", "s1"];

    const level_pendidikan_list = [
        {"level": 4, "title": ["s3", "doctor", "ph.d"]},
        {"level": 3, "title": ["s2", "m.", "master", "magister"]},
        {"level": 2, "title": ["s1", "s.", "sarjana", "bachelor"]},
        {"level": 1, "title": ["diploma"]}
    ];

    const threshold = 0.1;

    var nama = [];
    var skills = [];
    var experience = [];
    var pendidikan = [];

    function removeZeroColumns(data) {
        return data.map(arr => arr.filter((_, idx) => data.some(row => row[idx] !== 0)));
    }

    function getPendidikanTerakhir(listEdu) {
        let res = 0;
        listEdu.forEach(text => {
            pendidikan_list.forEach(word => {
                if (text.toLowerCase().includes(word.toLowerCase())) {
                    level_pendidikan_list.forEach(item => {
                        if (item.title.some(title => text.toLowerCase().includes(title.toLowerCase())) && item.level > res) {
                            res = item.level;
                        }
                    });
                }
            });
        });
        return res;
    }

    function preprocess(text) {
        // Membagi dan memproses teks menjadi token
        return text.toLowerCase().split(/\s+/);
    }

    function computeTF(doc) {
        // Menghitung frekuensi term (TF) untuk sebuah dokumen
        const tf = {};
        const docLength = doc.length;
        doc.forEach(term => {
            if (tf[term]) {
                tf[term] += 1;
            } else {
                tf[term] = 1;
            }
        });
        Object.keys(tf).forEach(term => {
            tf[term] = tf[term] / docLength;
        });
        return tf;
    }

    function computeIDF(documents) {
        // Menghitung inverse document frequency (IDF) untuk seluruh korpus
        const numDocs = documents.length;
        const idf = {};
        const allTerms = new Set(documents.flat());

        allTerms.forEach(term => {
            let containingDocs = 0;
            documents.forEach(doc => {
                if (doc.includes(term)) {
                    containingDocs += 1;
                }
            });
            idf[term] = Math.log(numDocs / (1 + containingDocs));
        });

        return idf;
    }

    function computeTFIDF(doc, idf) {
        // Menghitung TF-IDF untuk sebuah dokumen
        const tf = computeTF(doc);
        const tfidf = {};
        Object.keys(tf).forEach(term => {
            tfidf[term] = tf[term] * idf[term];
        });
        return tfidf;
    }

    function normalizeVector(tfidf) {
        // Menormalkan vektor TF-IDF menggunakan normalisasi Euclidean (L2)
        const norm = Math.sqrt(Object.values(tfidf).reduce((sum, score) => sum + score ** 2, 0));
        const normalizedTfidf = {};
        Object.keys(tfidf).forEach(term => {
            normalizedTfidf[term] = tfidf[term] / norm;
        });
        return normalizedTfidf;
    }

    function tfidfToVector(tfidf, terms) {
        // Mengonversi dokumen TF-IDF yang dinormalisasi ke dalam format vektor
        return terms.map(term => tfidf[term] || 0.0);
    }

    // Fungsi untuk menginisialisasi centroid secara acak
    function inisialisasiCentroid(data, k, seed) {
        if (seed !== null) {
            Math.seedrandom(seed);
        }
        return Array.from({ length: k }, () => data[Math.floor(Math.random() * data.length)]);
    }

    // Fungsi untuk menghitung jarak Euclidean antara dua titik
    function jarakEuclidean(a, b) {
        return Math.sqrt(a.reduce((acc, val, idx) => acc + (val - b[idx]) ** 2, 0));
    }

    // Fungsi untuk menetapkan titik data ke centroid terdekat
    function tetapkanCluster(data, centroid, nama) {
        const cluster = {};
        const owner = {};
        data.forEach((titik, idx) => {
            const jarak = centroid.map(c => cosineSimilarity(titik, c));
            const kluster = jarak.indexOf(Math.max(...jarak));
            if (kluster in cluster) {
                owner[kluster].push({
                    "nama":nama[idx],
                    "experience": experience[idx],
                    "skills": skills[idx],
                    "pendidikan": pendidikan[idx]
                });
                cluster[kluster].push(titik);
            } else {
                owner[kluster] = [{
                    "nama":nama[idx],
                    "experience": experience[idx],
                    "skills": skills[idx],
                    "pendidikan": pendidikan[idx]
                }];
                cluster[kluster] = [titik];
            }
        });
        return [owner, cluster];
    }

    // Fungsi untuk memperbarui centroid berdasarkan rata-rata titik dalam setiap kluster
    function perbaruiCentroid(cluster) {
        return Object.values(cluster).map(kluster => {
            const centroidBaru = Array(kluster[0].length).fill(0);
            kluster.forEach(titik => {
                for (let i = 0; i < titik.length; i++) {
                    centroidBaru[i] += titik[i];
                }
            });
            return centroidBaru.map(val => val / kluster.length);
        });
    }


    // Fungsi utama untuk menjalankan algoritma k-means
    function kMeans(data, k, iterasiMaks = 100, seed = null) {
        let centroid = inisialisasiCentroid(data, k, seed);
        let owner = {};
        let cluster = {}; 
        let converged = false;
        let iteration = 0;
        while (!converged) {
            const [newOwner, newCluster] = tetapkanCluster(data, centroid, nama);
            const centroidBaru = perbaruiCentroid(newCluster);
            converged = JSON.stringify(centroidBaru) === JSON.stringify(centroid);
            if (JSON.stringify(centroidBaru) === JSON.stringify(centroid)) {
                break;
            }
            iteration++;
            centroid = centroidBaru;
            owner = newOwner;
            cluster = newCluster;
            console.log(iteration)
            // console.log("centroid"+JSON.stringify(centroid))
        }

        let result = {};

        for(let i = 0; i < Object.keys(owner).length; i++){
            let temp = [];
            for(let j = 0; j < owner[i].length; j++){
                temp.push({
                    "owner": owner[i][j],
                    "data": cluster[i][j]
                })
            
            }
            result[i] = temp;
        }

        return [result, centroid];
    }


    // Fungsi untuk menghitung kesamaan kosinus antara dua vektor
    function cosineSimilarity(vec1, vec2) {
        const dotProduct = vec1.reduce((acc, val, idx) => acc + val * vec2[idx], 0);
        const magnitude1 = Math.sqrt(vec1.reduce((acc, val) => acc + val ** 2, 0));
        const magnitude2 = Math.sqrt(vec2.reduce((acc, val) => acc + val ** 2, 0));
        if (magnitude1 === 0 || magnitude2 === 0) {
            return 0;
        }
        return dotProduct / (magnitude1 * magnitude2);
    }








    $(document).ready(function() {
        $.getJSON("data.json", function(data) {
                // Example of using the data
                let idx = 1;
                data.forEach(element => {
                    $("#table-data").append(`
                        <tr>
                            <th scope="row">`+(idx)+`</th>
                            <td>`+(element.Name)+`</td>
                            <td>`+(element.Skills)+`</td>
                            <td>`+(element.Pendidikan)+`</td>
                            <td>`+(element.Experience)+`</td>
                        </tr>
                    `);
                    idx = idx + 1;

                    nama.push(element.Name);

                    if (Array.isArray(element.Skills)) {
                        skills.push(element.Skills.join(" "));
                    } else {
                        skills.push(element.Skills);
                    }

                    if (Array.isArray(element.Experience)) {
                        experience.push(element.Experience.join(" "));
                    } else {
                        experience.push(element.Experience);
                    }

                    if (element.Pendidikan.length > 0) {
                        const res = getPendidikanTerakhir(element.Pendidikan);
                        pendidikan.push(res);
                    } else {
                        pendidikan.push(0);
                    }
                });

        }).fail(function() {
            console.error("An error occurred while loading the JSON file.");
        });


        $("#myButton").click(function() {
            // Memproses dokumen
            const preprocessedSkills = skills.map(doc => preprocess(doc));

            // Menghitung IDF untuk seluruh korpus
            const idfSkills = computeIDF(preprocessedSkills);

            // Menghitung dan menormalkan TF-IDF untuk setiap dokumen
            const tfidfSkills = preprocessedSkills.map(doc => normalizeVector(computeTFIDF(doc, idfSkills)));

            const termsSkills = Object.keys(idfSkills);
            var vectorsSkills = tfidfSkills.map(tfidf => tfidfToVector(tfidf, termsSkills));

            vectorsSkills = removeZeroColumns(vectorsSkills.map(row => row.map(value => value >= threshold ? 1 : 0)));

            // Memproses dokumen
            const preprocessedExp = experience.map(doc => preprocess(doc));

            // Menghitung IDF untuk seluruh korpus
            const idfExp = computeIDF(preprocessedExp);

            // Menghitung dan menormalkan TF-IDF untuk setiap dokumen
            const tfidfExp = preprocessedExp.map(doc => normalizeVector(computeTFIDF(doc, idfExp)));

            const termsExp = Object.keys(idfExp);
            var vectorsExp = tfidfExp.map(tfidf => tfidfToVector(tfidf, termsExp));

            vectorsExp = removeZeroColumns(vectorsExp.map(row => row.map(value => value >= threshold ? 1 : 0)));


            console.log(vectorsSkills)
            console.log(vectorsExp)

            // Membuat vektor fitur
            const featureVectors = nama.map((item, index) => {
                let features = [pendidikan[index], ...vectorsSkills[index], ...vectorsExp[index]];
                return features;
            });

            console.log(featureVectors)

            // Menetapkan jumlah cluster dan seed
            const k = 2;
            const seed = nama.length / 2;

            // Menerapkan k-means clustering
            const [result, centroids] = kMeans(featureVectors, k, 9999, seed);

            $('#kmeans-result').empty();

            Object.keys(result).map(doc => {
                let idx = 1;
                let tes = [];
                $("#kmeans-result").append(`
                    <h3>`+("Kluster "+(parseInt(doc)+1))+`</h3>
                    <table class="table">
                    <thead>
                        <tr>
                            <th scope="col">#</th>
                            <th scope="col">Nama</th>
                            <th scope="col">Skills</th>
                            <th scope="col">Pendidikan</th>
                            <th scope="col">Pengalaman</th>
                            <th scope="col">Kesamaan Kosinus</th>

                        </tr>
                    </thead>
                    <tbody id=`+("kmeans-tbl-"+doc)+`></tbody>
                    </table>
                `);

                result[doc].map(res => {
                    $(("#kmeans-tbl-"+doc)).append(`<tr>
                        <th scope="row">`+(idx)+`</th>
                        <td>`+(res.owner.nama)+`</td>
                        <td>`+(res.owner.skills)+`</td>
                        <td>`+(res.owner.pendidikan)+`</td>
                        <td>`+(res.owner.experience)+`</td>
                        <td>`+("Kesamaan Kosinus untuk Index "+idx+" dalam cluster "+(parseInt(doc)+1)+": "+cosineSimilarity(res.data, centroids[doc])+"")+`</td>
                    </tr>`);

                    tes.push("Kesamaan Kosinus untuk Index "+idx+" dalam cluster "+(parseInt(doc)+1)+": "+cosineSimilarity(res.data, centroids[doc]))

                    idx = idx + 1;
                });
            });
        });



    });
</script>
</body>
</html>