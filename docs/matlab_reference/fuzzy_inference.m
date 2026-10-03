
% Fuzzy-inference technique to calculate the relative weights both indicators and categories
% For: Jose Daniel Hernandez Betancur
% Master thesis' title: "Detection of the critcal points of hot-dip galvanizing process:
% a focus on sustainability and sustainable development
% Master degree's name: Master in Engineering - Materials and Processes
% University: National University of Colombia - Medellin branch
% Date: 19 April, 2017
%%-----------------------------------------------------------------------------------------------------------

function [W,theta] = fuzzy_inference(n,mm,calc)

% n is the number of indicators (or categories)
% mm is the number of decision-makers
% calc is the spreadsheet (1) categories, (2) effiency and (3) environment

% Triangular fuzzy numbers (TFN)
% TFN is a vector with n segments and each one has 3 different numbers
% The segments are the linguistic scales
% The 3 differente numbers in the segments are a triangular fuzzy number (l,m,u)
% The first segment: equal importance;
% The second one: moderate importance of one over another;
% The third one: strong importance of one over another;
% The fourth one: very strong importance of one over another
% The fifth one: absolute importance of one over another

TFN = [1 1 1 2/3 1 3/2 3/2 2 5/2 5/2 3 7/2 7/2 4 9/2];

%% Calculating of relative weights of categories or indicators

% (1) Import imformation

if calc == 1
sheet = 'Sheet1';
cellsin = 'B2:F36';
cellsout = 'I2:I6';
elseif calc == 2
sheet = 'Sheet2';
cellsin = 'B2:F29';
cellsout = 'H2:H5';
elseif calc == 3
sheet = 'Sheet3';
cellsin = 'B2:L78';
cellsout = 'O2:O12';
end

N = xlsread('categorias.xlsx',sheet,cellsin);

% Definition of variables

W = zeros(1,n); % initial value of weights vector (desired output)
w = zeros(mm,n); % initial value of weithts matrix
phi = zeros(mm,1); % diversification degree
eps1 = zeros(mm,1); % entropy
theta = zeros(1,mm); % experts' uncertainty degrees
sumphi = 0; % Initial value of diversification degree sum

for k = 1:mm

% (2) Comparison matrix (In this case is a vector because of computational memory)
for i = k*n-(n-1):k*n

for j = i-n*(k-1):n

% This is the position of the third element of the segment for
% a*(i,j) (upper triangular part)
jj = 3*(n*((i-n*(k-1))-1)+j);

% This is the position of the thrid element of the segment for
% a*(j,i) (lower triangular part)
jjj = 3*(n*(j-1) + i-n*(k-1));

if N(i,j) == -4

a(jjj-2:jjj) = TFN(13:15);
a(jj-2:jj) = [TFN(15)^-1 TFN(14) TFN(13)^-1];

elseif N(i,j) == -3

a(jjj-2:jjj) = TFN(10:12);
a(jj-2:jj) = [TFN(12)^-1 TFN(11) TFN(10)^-1];

elseif N(i,j) == -2

a(jjj-2:jjj) = TFN(7:9);
a(jj-2:jj) = [TFN(9)^-1 TFN(8) TFN(7)^-1];

elseif N(i,j) == -1

a(jjj-2:jjj) = TFN(4:6);
a(jj-2:jj) = [TFN(6)^-1 TFN(5) TFN(4)^-1];

elseif N(i,j) == 0

a(jj-2:jj) = TFN(1:3);
a(jjj-2:jjj) = TFN(1:3);

elseif N(i,j) == 1

a(jj-2:jj) = TFN(4:6);
a(jjj-2:jjj) = [TFN(6)^-1 TFN(5) TFN(4)^-1];

elseif N(i,j) == 2

a(jj-2:jj) = TFN(7:9);
a(jjj-2:jjj) = [TFN(9)^-1 TFN(8) TFN(7)^-1];

elseif N(i,j) == 3

a(jj-2:jj) = TFN(10:12);
a(jjj-2:jjj) = [TFN(12)^-1 TFN(11) TFN(10)^-1];

elseif N(i,j) == 4

a(jj-2:jj) = TFN(13:15);
a(jjj-2:jjj) = [TFN(15)^-1 TFN(14) TFN(13)^-1];

end

end

end

clear i
clear j

% (3) Fuzzy synthetic extension

A = zeros(n,3);
B = zeros(1,3);

for i = 1:n

for j = 1:n

jj = 3*(n*(i-1)+j);

A(i,:) = A(i,:) + a(jj-2:jj);

end

B = B + A(i,:);

end

clear i
clear j

BB = [B(3)^-1 B(2) B(1)^-1];
S = zeros(n,3);

for i = 1:n

for j = 1:3

S(i,j) = A(i,j)*B(j) ;

end

end

clear i
clear j

% (4) Degree of possibility

for i = 1:n

for j = 1:n

if S(i,2) >= S(j,2)

V(j) = 1;

elseif S(j,1) >= S(i,3)

V(j) = 0;

else

V(j) = (S(j,1) - S(i,3))/((S(i,2)-S(i,3))-(S(j,2)-S(j,1)));

end

end

w1(i) = min(V);

end

clear i
clear j

% (5) Weight of a category or indicator for a expert
w(k,:) = (sum(w1)^-1)*w1;

% (6) Experts' uncertainty degrees

for i = 1:n

if w(k,i) ~= 0 eps1(k) = eps1(k) + w(k,i)*log(w(k,i)); end

end

eps1(k) = eps1(k)/log(n);
phi(k) = 1 + eps1(k);

sumphi = sumphi + phi(k);


end

clear k

% (7) Final weight of all categories or indicators

for i = 1:n

for k = 1:mm

theta(1,k) = phi(k)/sumphi;
W(1,i) = W(1,i) + w(k,i)*theta(1,k);

end

end

W = (sum(W)^-1)*W; % Final weight

% (8) Save the information
xlswrite('categorias.xlsx',W',sheet,cellsout);

return
