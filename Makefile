demo:	build base-container demo-container


build :
	docker build -t sr-demo .


base-container:
	#python RenderASBRConfigs.py
	docker network create --driver=bridge --subnet=192.168.1.0/24 sr-net
	docker run -d -it --network=sr-net --ip=192.168.1.2 --dns=8.8.8.8 \
	--volume `pwd`:/home/demo/sr-demo \
	-p 179:179 \
	-p 4200:4200 \
	-p 5000:5000 \
	-p 5001:5001 \
	--name srbase sr-demo
	#docker exec -d srbase python sr-base-docker.py

demo-container:
	docker run --name srdemo --rm -t --network=sr-net --ip=192.168.1.3 --dns=8.8.8.8 \
	--volume `pwd`:/home/demo/sr-demo \
        -i sr-demo bash

term:
	docker run --rm -t --network=sr-net --dns=8.8.8.8 \
	--volume `pwd`:/home/demo/sr-demo \
        -i sr-demo bash

clean:
	docker stop srbase
	docker rm srbase
	docker network rm sr-net
