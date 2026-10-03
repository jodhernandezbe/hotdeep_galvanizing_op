
%% Hierarchical partitioning to calculate the critical points of hot-dip galvanizing
% For: Jose Daniel Hernandez Betancur
% Mater thesis title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 22 July, 2017
%%-----------------------------------------------------------------------------------------------------------

function [I,J,countn] = hierarchical_partitioning(y,x,ID,countn)

% y is a vector with n values for dependent variable (response variable)
% x is a matrix with n values for each m independent variable (predictor variable)
% ID is a number of identification which says if this process is done for
% the unit processes inside hot-dip galvanizing (1) or for the metrics set (2)

%%-----------------------------------------------------------------------------------------------------------

% Note:
%
% (1) According to hierarchical partitioning analysis, there are 2^m possible
% models; therefore, there is the same amount of coefficients of
% determination (R^2)
% (2) There are m+1 hierarchical levels of model complexity
% (3) There are m! hierarchical ordering each one with m differences

%%-----------------------------------------------------------------------------------------------------------

% Constrution of linear regressions and R^2
m = size(x,2);

MAX = 0;
for i=1:m

LL = factorial(m)/factorial(m - i);

if LL > MAX

MAX = LL;

end

end

clear i

R2 = zeros(m+1,MAX);

for i = 1:m

XX = ones(size(x,1),i+1); % i+1 because there is an additional column

L = factorial(m)/factorial(m-i); % # equations at the level
position = zeros(L,i);
position = combinator(m,i,'p'); % permutations of position at a level
position = sortrows(position);

for j = 1:L

for k=1:i

XX(:,k+1) = x(:,position(j,k));

end

% Coefficient of determination (R^2)
A = XX'*XX;
K = inv(A);
beta = K*XX'*y;
M = XX*beta;

R2(i+1,j) = var(M)/var(y);

end

end

clear i
clear j
clear k

% Independent effect of each variable
I = zeros(m,1);
D = zeros(m,1);

for i = 1:m % independent variable

nn = ones(m+1,1);
cont = zeros(m+1,1);

for j = 1:factorial(m-1) % column

for k = 1:m % differences

LL = factorial(m)/(m*factorial(m-k));

if cont(k+1,1) == factorial(m-1)/LL

cont(k+1,1) = 0;
nn(k+1,1) = nn(k+1,1) + 1;

end

left = (i - 1)*LL + nn(k+1,1);

D(i,1) = D(i,1) + R2(k+1,left);

cont(k+1,1) = cont(k+1,1) + 1;

end

end

end

clear i
clear j
clear k

for i = 1:m

for k = 1:m-1

XX1 = ones(size(x,1),k + 1);
vector_aux = zeros(m-1,1);
mm = 1;

L = factorial(m-1)/(factorial(k)*factorial((m-1)-k));
position = zeros(L,k);

for j = 1:m

if j ~= i

vector_aux(mm,1) = j;
mm = mm + 1;

end

end

position = combntns(vector_aux,k); % combinations of positions at level

for jj = 1:L

for kk=1:k

XX1(:,kk+1) = x(:,position(jj,kk));

end

A = XX1'*XX1;
K = inv(A);
beta = K*XX1'*y;
M = XX1*beta;

D(i,1) = D(i,1) - (factorial(m-1)/L)*var(M)/var(y);

end

end

end

clear i
clear k
clear j
clear jj
clear kk

I = (1/(m*factorial(m-1)))*D;
sum_Ic = sum(I);

% Joint effect of each variable

J = zeros(m,1);
sum_Rc = sum(R2(2,:)); % sum of zero-order associations

sum_Jc = sum_Rc - sum_Ic; % sum of joint effect of predictor variables

J(:,1) = R2(2,1:m)' - I(:,1);

% Final results
I = (100/sum_Ic)*I;
J = (100/sum_Jc)*J;

% Figures

if ID == 1

Aux = 'U';
Aux1 = 'Procesos unitarios';
Aux2 = 'Analisis de Pareto para procesos unitarios';

else

Aux = 'G';
Aux1 = 'Metricas';
Aux2 = 'Analisis de Pareto para metricas';

end

for j = 1:m

BB{j} = num2str(j);
BB{j} = strcat(Aux,BB{j});

end

countn = countn + 1;
figure(countn) % Independent contribution [ %]

bar(I,0.6,'FaceColor',[0 .5 .5],'EdgeColor',[0 .5 .5],'LineWidth',1.5)
set(gca,'XTickLabel',BB)
ylabel('Efecto independiente [ %]','FontSize',12,'FontWeight','bold')
xlabel(Aux1,'FontSize',12,'FontWeight','bold')

axis([0 m+1 0 5*round(max(I)/5)+5])

xx = 1:1:m;

for i1=1:numel(I)
text(xx(i1),I(i1)+ 0.5,strcat(num2str(I(i1),' %0.4f'),' %'),...
'HorizontalAlignment','center',...
'VerticalAlignment','bottom')
end
clear i1

set(gca,'ygrid','on')

hold off

countn = countn + 1;
figure(countn) % Explained Variance

T = tinv(0.995,size(x,1)-2); % Critical value with n-2 freedom dregees and a significance level of 0.01
rr2 = T^2/(size(x,1)-2+T^2);

I_aux = 0.01*sum_Ic*I; max_I_aux = max(I_aux); I_aux = (1/max_I_aux)*I_aux;
J_aux = (0.01*sum_Jc/max_I_aux)*J;

yy = [I_aux J_aux R2(2,1:m)'];
clr = [1 1 0;0.3 0.8 0.8;0 0 1];
colormap(clr);
bar(yy,1,'LineWidth',.01)
set(gca,'XTickLabel',BB)
ylabel('Varianza explicada','FontSize',12,'FontWeight','bold')
xlabel(Aux1,'FontSize',12,'FontWeight','bold')
set(gca,'ygrid','on')

hold on

aa1 = linspace(0,m+1);
aa2 = rr2*ones(length(aa1),1);
plot(aa1,aa2,'r:','LineWidth',2.5)

legend({'I_{i}','J_{i}','R_{yi}^{2}','V_{C}'},'Location','NorthWest');

hold off

countn = countn + 1;
figure(countn) % Pareto analysis

colormap([.8 .5 1]);
pareto(I,BB)
title(Aux2,'FontSize',12,'FontWeight','bold')
xlabel(Aux1,'FontSize',12,'FontWeight','bold')
ylabel('Efecto independiente [ %]','FontSize',12,'FontWeight','bold')
set(gca,'ygrid','on')
hold on

zz1 = linspace(0,m+1);
zz2 = 80*ones(length(zz1),1);
plot(zz1,zz2,'r:','LineWidth',2.5)
hold on

II = sort(I,'descend');
for i=2:m

II(i) = II(i) + II(i-1);

end

vq1 = interp1(II,1:m,80);
zz4 = linspace(0,100);
zz3 = vq1*ones(length(zz4),1);
plot(zz3,zz4,'r:','LineWidth',2.5)

legend('Efecto independiente [ %]','Porcentaje acumulado [ %]','Linea de 80 %','Location','NorthWest')

hold off

return
